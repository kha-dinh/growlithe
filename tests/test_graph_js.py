import os
import unittest
from growlithe.cli.analyze import analyze
from growlithe.config import get_config
from growlithe.graph.adg.edge import EdgeType


class TestGraphJS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the path to the sample_app_js directory
        cls.sample_app_dir = os.path.join(current_dir, "sample_app_js")
        # Construct the path to growlithe_config.yaml
        cls.custom_config_path = os.path.join(
            cls.sample_app_dir, "growlithe_config.yaml"
        )

        cls.config = get_config(os.path.abspath(cls.custom_config_path))
        cls.graph = analyze(cls.config)

    def test_graph_structure(self):
        """Test basic graph structure: functions, nodes, edges counts."""
        self.assertEqual(len(self.graph.functions), 2)
        self.assertGreater(len(self.graph.nodes), 0)

    def test_function_names(self):
        """Test that expected functions are discovered."""
        function_names = {f.name for f in self.graph.functions}
        self.assertIn("Function1", function_names)
        self.assertIn("Function2", function_names)

    def test_parameter_nodes_exist(self):
        """Test that parameter nodes (event handlers) are detected."""
        param_nodes = [n for n in self.graph.nodes if n.object_type == "PARAM"]
        # Should have at least one param node per function
        self.assertGreaterEqual(
            len(param_nodes), len(self.graph.functions),
            "Not enough parameter nodes detected for functions"
        )

    def test_return_nodes_exist(self):
        """Test that return nodes are detected."""
        return_nodes = [n for n in self.graph.nodes if n.object_type == "RETURN"]
        self.assertGreater(
            len(return_nodes), 0,
            "No return nodes detected"
        )

    def test_each_function_has_nodes(self):
        """Test that each function has associated nodes."""
        for func in self.graph.functions:
            func_nodes = [n for n in self.graph.nodes if n.object_fn == func]
            self.assertGreater(
                len(func_nodes), 0,
                f"Function {func.name} has no associated nodes"
            )

    def test_edges_reference_valid_nodes(self):
        """Test that all edges reference nodes that exist in the graph."""
        node_set = set(self.graph.nodes)
        for edge in self.graph.edges:
            self.assertIn(
                edge.source, node_set,
                f"Edge source {edge.source} not in graph nodes"
            )
            self.assertIn(
                edge.sink, node_set,
                f"Edge sink {edge.sink} not in graph nodes"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
