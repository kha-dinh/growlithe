import os
import unittest
from growlithe.cli.analyze import analyze
from growlithe.config import get_config
from growlithe.graph.adg.edge import EdgeType


class TestGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the path to the sample_app directory
        cls.sample_app_dir = os.path.join(current_dir, "sample_app")
        # Construct the path to growlithe_config.yaml
        cls.custom_config_path = os.path.join(
            cls.sample_app_dir, "growlithe_config.yaml"
        )

        cls.config = get_config(os.path.abspath(cls.custom_config_path))
        cls.graph = analyze(cls.config)

    def test_graph_structure(self):
        """Test basic graph structure: functions, nodes, edges counts."""
        self.assertEqual(len(self.graph.functions), 2)
        self.assertEqual(len(self.graph.edges), 7)
        self.assertGreater(len(self.graph.nodes), 0)

    def test_function_names(self):
        """Test that expected functions are discovered."""
        function_names = {f.name for f in self.graph.functions}
        self.assertIn("Function1", function_names)
        self.assertIn("Function2", function_names)

    def test_s3_download_source_detected(self):
        """Test that S3 bucket download operations are detected as sources."""
        s3_download_nodes = [
            n for n in self.graph.nodes
            if n.object_type == "S3_BUCKET" and n.is_source
        ]
        self.assertGreater(
            len(s3_download_nodes), 0,
            "No S3 download sources detected - CodeQL query may not be finding S3BucketDownload"
        )

    def test_s3_upload_sink_detected(self):
        """Test that S3 bucket upload operations are detected as sinks."""
        s3_upload_nodes = [
            n for n in self.graph.nodes
            if n.object_type == "S3_BUCKET" and n.is_sink
        ]
        self.assertGreater(
            len(s3_upload_nodes), 0,
            "No S3 upload sinks detected - CodeQL query may not be finding S3BucketUpload"
        )

    def test_local_file_nodes_detected(self):
        """Test that local file operations are detected."""
        local_file_nodes = [
            n for n in self.graph.nodes
            if n.object_type == "LOCAL_FILE"
        ]
        self.assertGreater(
            len(local_file_nodes), 0,
            "No local file nodes detected"
        )

    def test_s3_to_localfile_flow_exists(self):
        """Test that dataflow from S3 download to local file is detected."""
        s3_to_local_edges = [
            e for e in self.graph.edges
            if e.source.object_type == "S3_BUCKET"
            and e.sink.object_type == "LOCAL_FILE"
        ]
        self.assertGreater(
            len(s3_to_local_edges), 0,
            "No S3 -> local file dataflow detected"
        )

    def test_localfile_to_s3_flow_exists(self):
        """Test that dataflow from local file to S3 upload is detected."""
        local_to_s3_edges = [
            e for e in self.graph.edges
            if e.source.object_type == "LOCAL_FILE"
            and e.sink.object_type == "S3_BUCKET"
        ]
        self.assertGreater(
            len(local_to_s3_edges), 0,
            "No local file -> S3 dataflow detected"
        )

    def test_data_edges_have_correct_type(self):
        """Test that detected edges have the correct edge type."""
        data_edges = [e for e in self.graph.edges if e.edge_type == EdgeType.DATA]
        self.assertGreater(
            len(data_edges), 0,
            "No DATA type edges found"
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
