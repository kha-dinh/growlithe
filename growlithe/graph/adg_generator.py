import os
from typing import List
from growlithe.graph.adg.edge import Edge, EdgeType
from growlithe.graph.adg.graph import Graph
from growlithe.graph.adg.node import Node
from growlithe.graph.adg.function import Function
from growlithe.graph.adg.resource import Resource, ResourceType
from growlithe.graph.adg.types import Scope
from growlithe.graph.parsers.sarif import SarifParser
from growlithe.common.logger import logger
from growlithe.config import Config


class GraphGenerator:
    def __init__(self, graph: Graph, config: Config):
        self.graph: Graph = graph
        self.config = config

    def _detect_language(self, functions: List[Function]) -> str:
        """Detect the language from function runtimes."""
        if not functions:
            return "python"
        runtime = functions[0].runtime.lower()
        if "python" in runtime:
            return "python"
        elif "node" in runtime:
            return "javascript"
        return "python"

    def generate_intrafunction_graphs(self, functions: List[Function]):
        language = self._detect_language(functions)
        logger.info(f"Generating dataflows for {len(functions)} functions.")
        sarif_parser = SarifParser(
            os.path.join(self.config.growlithe_path, f"dataflows_{language}.sarif"),
            self.config,
        )
        for function in functions:
            function_dataflows = sarif_parser.get_results_for_function(function)
            function.add_sarif_results(function_dataflows)
            for result in function_dataflows:
                sarif_parser.parse_sarif_result(
                    result, self.graph, function, EdgeType.DATA
                )

    def add_inter_function_edges(self, resources: List[Resource]):
        function_pairs = []
        trigger_pairs = []  # (trigger_resource, target_function)
        for source in resources:
            for target in source.dependencies:
                # source -> target
                if isinstance(target, Function):
                    if isinstance(source, Function):
                        # Function chain
                        self.connect_functions(source, target)
                        function_pairs.append((source, target))
                    else:
                        # trigger
                        self.handle_trigger(source, target)
                        trigger_pairs.append((source, target))
                else:
                    # should not happen
                    logger.error(
                        f"{source.name}:{source.type} -> {target.name}:{target.type} is not supported."
                    )

        # Derive function chains from LAMBDA_INVOKE nodes detected by CodeQL
        for node in self.graph.nodes:
            if node.object_type == "LAMBDA_INVOKE" and node.is_sink:
                source_fn = node.object_fn
                if source_fn is None:
                    continue
                resource_name = str(node.resource)
                for resource in resources:
                    if isinstance(resource, Function) and resource.name in resource_name:
                        target_event = resource.get_event_node()
                        if target_event is not None:
                            # Connect LAMBDA_INVOKE sink directly to target's event node
                            edge = Edge(
                                u=node,
                                v=target_event,
                                source_code_path=node.object_code_location,
                                sink_code_path=target_event.object_code_location,
                                function=source_fn,
                                edge_type=EdgeType.INDIRECT,
                            )
                            self.graph.add_edge(edge)
                        if (source_fn, resource) not in function_pairs:
                            function_pairs.append((source_fn, resource))
                            logger.debug(f"Derived function pair from LAMBDA_INVOKE: {source_fn.name} -> {resource.name}")
                        break

        self.add_potential_resources(resources)

        # Add indirect edges from trigger sources: any function writing to the trigger
        # resource has an indirect flow into the triggered function's event node.
        for trigger_resource, target_fn in trigger_pairs:
            target_event = target_fn.get_event_node()
            if target_event is None:
                continue
            for node in self.graph.nodes:
                if (
                    node.scope == Scope.GLOBAL
                    and node.is_sink
                    and node.object_fn is not None
                    and node.object_fn != target_fn
                ):
                    potential = node.resource_attrs.get("potential_resources", [])
                    if trigger_resource in potential:
                        edge = Edge(
                            u=node,
                            v=target_event,
                            source_code_path=node.object_code_location,
                            sink_code_path=target_event.object_code_location,
                            function=node.object_fn,
                            edge_type=EdgeType.INDIRECT,
                        )
                        self.graph.add_edge(edge)
                        logger.debug(
                            f"Trigger indirect edge: {node} -> {target_event} via {trigger_resource.name}"
                        )
                        pair = (node.object_fn, target_fn)
                        if pair not in function_pairs:
                            function_pairs.append(pair)

        for source, target in function_pairs:
            self.add_potential_indirect_flows(source, target)

    def add_potential_resources(self, resources):
        for node in self.graph.nodes:
            if (
                node.object_type == "S3_BUCKET"
                and "potential_resources" not in node.resource_attrs
            ):
                potential_resources = []
                for resource in resources:
                    if resource.type == ResourceType.S3_BUCKET:
                        potential_resources.append(resource)
                node.resource_attrs["potential_resources"] = potential_resources
            elif (
                node.object_type == "DYNAMODB_TABLE"
                and "potential_resources" not in node.resource_attrs
            ):
                potential_resources = []
                for resource in resources:
                    if resource.type == ResourceType.DYNAMODB_TABLE:
                        potential_resources.append(resource)
                node.resource_attrs["potential_resources"] = potential_resources
            elif (
                node.object_type == "LAMBDA_INVOKE"
                and "potential_resources" not in node.resource_attrs
            ):
                potential_resources = []
                for resource in resources:
                    if resource.type == ResourceType.FUNCTION:
                        potential_resources.append(resource)

                node.resource_attrs["potential_resources"] = potential_resources
                logger.warn(f"{node} {potential_resources}")

            if node.resource_attrs:
                logger.debug(f"{node} {node.resource_attrs}")

    def add_metadata_edges(self, functions: List[Function]):
        language = self._detect_language(functions)
        sarif_parser = SarifParser(
            os.path.join(self.config.growlithe_path, f"metadataflows_{language}.sarif"),
            self.config,
        )
        edge_type = EdgeType.METADATA
        if self.config.has_key("benchmark_name") and (
            self.config.benchmark_name.startswith("Benchmark1")
            or self.config.benchmark_name.startswith("Benchmark3")
        ):
            edge_type = EdgeType.DATA

        for function in functions:
            function_metadataflows = sarif_parser.get_results_for_function(function)
            # function.add_sarif_results(function_metadataflows)
            for result in function_metadataflows:
                sarif_parser.parse_sarif_result(result, self.graph, function, edge_type)

    def connect_functions(self, source: Function, target: Function):
        source_ret: Node = source.get_return_node()
        target_event: Node = target.get_event_node()
        edge = Edge(
            u=source_ret,
            v=target_event,
            source_code_path=source_ret.object_code_location,
            sink_code_path=target_event.object_code_location,
            function=source,
            edge_type=EdgeType.INDIRECT,
        )
        self.graph.add_edge(edge)

    def handle_trigger(self, source: Resource, target: Function):
        # S3 trigger
        if source.type == ResourceType.S3_BUCKET:
            self.append_resource_metadata(source)
        if source.type == ResourceType.DYNAMODB_TABLE:
            self.append_resource_metadata(source)

    def append_resource_metadata(self, resource: Resource):
        """
        Add potential resource to the node inside the function that represents the resource
        :param resource: Resource
        """
        for node in self.graph.nodes:
            if node.object_type == resource.type.name:
                if "potential_resources" in node.resource_attrs:
                    node.resource_attrs["potential_resources"].append(resource)
                else:
                    node.resource_attrs["potential_resources"] = [resource]

    def add_potential_indirect_flows(self, source: Function, target: Function):
        """
        Add indirect edges from all the nodes in the source function to all the nodes in the sink function that share potential resources.
        :param source: source function
        :param target: target function
        """
        for node1 in self.graph.nodes:
            if (
                node1.object_fn == source
                and node1.scope == Scope.GLOBAL
                and node1.is_sink
            ):
                for node2 in self.graph.nodes:
                    if (
                        node2.object_fn == target
                        and node2.scope == Scope.GLOBAL
                        and node2.is_source
                    ):
                        if (
                            "potential_resources" in node1.resource_attrs
                            and "potential_resources" in node2.resource_attrs
                        ):
                            for resource in node1.resource_attrs["potential_resources"]:
                                if (
                                    resource
                                    in node2.resource_attrs["potential_resources"]
                                ):
                                    edge = Edge(
                                        u=node1,
                                        v=node2,
                                        source_code_path=node1.object_code_location,
                                        sink_code_path=node2.object_code_location,
                                        function=source,
                                        edge_type=EdgeType.INDIRECT,
                                    )
                                    self.graph.add_edge(edge)
