import os
import unittest
from growlithe.cli.analyze import analyze
from growlithe.config import Config, get_config
from growlithe.graph.adg.edge import EdgeType


def _config_path(app_dir):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), app_dir, "growlithe_config.yaml")


def _fresh_config(path):
    """Reset the Config singleton so each test class gets its own config."""
    Config._instance = None
    return get_config(os.path.abspath(path))


class TestDataEdges(unittest.TestCase):
    """DATA edges: intra-function flows detected by CodeQL dataflow analysis."""

    @classmethod
    def setUpClass(cls):
        cls.graph = analyze(_fresh_config(_config_path("sample_app")))
        cls.data_edges = [e for e in cls.graph.edges if e.edge_type == EdgeType.DATA]

    def test_data_edges_exist(self):
        self.assertGreater(len(self.data_edges), 0)

    def test_s3_download_to_localfile_is_data(self):
        edges = [
            e for e in self.data_edges
            if e.source.object_type == "S3_BUCKET" and e.sink.object_type == "LOCAL_FILE"
        ]
        self.assertGreater(len(edges), 0, "No DATA edge from S3_BUCKET to LOCAL_FILE")

    def test_localfile_to_s3_upload_is_data(self):
        edges = [
            e for e in self.data_edges
            if e.source.object_type == "LOCAL_FILE" and e.sink.object_type == "S3_BUCKET"
        ]
        self.assertGreater(len(edges), 0, "No DATA edge from LOCAL_FILE to S3_BUCKET")

    def test_param_to_return_is_data(self):
        edges = [
            e for e in self.data_edges
            if e.source.object_type == "PARAM" and e.sink.object_type == "RETURN"
        ]
        self.assertGreater(len(edges), 0, "No DATA edge from PARAM to RETURN")

    def test_data_edges_are_intrafunction(self):
        """DATA edges from CodeQL analysis must stay within a single function."""
        for edge in self.data_edges:
            self.assertEqual(
                edge.source.object_fn,
                edge.sink.object_fn,
                f"DATA edge {edge} should not cross function boundary",
            )

    def test_data_edge_nodes_in_graph(self):
        node_set = set(self.graph.nodes)
        for edge in self.data_edges:
            self.assertIn(edge.source, node_set)
            self.assertIn(edge.sink, node_set)


class TestMetadataEdges(unittest.TestCase):
    """METADATA edges: flows where only a key/selector (not the payload) comes from the source.
    Stored in graph.metadata_edges, separate from graph.edges."""

    @classmethod
    def setUpClass(cls):
        claim_config = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "benchmarks", "ClaimProcessing", "growlithe_config.yaml",
        )
        cls.graph = analyze(_fresh_config(claim_config))
        cls.metadata_edges = cls.graph.metadata_edges

    def test_metadata_edges_exist(self):
        self.assertGreater(len(self.metadata_edges), 0)

    def test_metadata_edges_not_in_data_list(self):
        """METADATA edges must be stored in graph.metadata_edges, not graph.edges."""
        for edge in self.metadata_edges:
            self.assertNotIn(
                edge, self.graph.edges,
                "METADATA edge found in graph.edges — should be in graph.metadata_edges only",
            )

    def test_metadata_edges_have_correct_type(self):
        for edge in self.metadata_edges:
            self.assertEqual(edge.edge_type, EdgeType.METADATA)

    def test_event_to_dynamodb_metadata_flow(self):
        """Event parameter used as a DynamoDB query key should produce a METADATA edge."""
        edges = [
            e for e in self.metadata_edges
            if e.source.object_type == "PARAM" and e.sink.object_type == "DYNAMODB_TABLE"
        ]
        self.assertGreater(
            len(edges), 0,
            "No METADATA edge from PARAM to DYNAMODB_TABLE",
        )

    def test_metadata_edges_are_intrafunction(self):
        """METADATA edges from CodeQL must stay within a single function."""
        for edge in self.metadata_edges:
            self.assertEqual(
                edge.source.object_fn,
                edge.sink.object_fn,
                f"METADATA edge {edge} should not cross function boundary",
            )

    def test_metadata_edge_nodes_in_graph(self):
        node_set = set(self.graph.nodes)
        for edge in self.metadata_edges:
            self.assertIn(edge.source, node_set)
            self.assertIn(edge.sink, node_set)


class TestIndirectEdges(unittest.TestCase):
    """INDIRECT edges: inter-function flows via state-machine chains or shared resources."""

    @classmethod
    def setUpClass(cls):
        cls.graph = analyze(_fresh_config(_config_path("sample_app")))
        cls.indirect_edges = [e for e in cls.graph.edges if e.edge_type == EdgeType.INDIRECT]

    def test_indirect_edges_exist(self):
        self.assertGreater(len(self.indirect_edges), 0)

    def test_indirect_edges_have_correct_type(self):
        for edge in self.indirect_edges:
            self.assertEqual(edge.edge_type, EdgeType.INDIRECT)

    def test_function_chain_connects_return_to_param(self):
        """State-machine function chain must create a RETURN → PARAM INDIRECT edge."""
        edges = [
            e for e in self.indirect_edges
            if e.source.object_type == "RETURN" and e.sink.object_type == "PARAM"
        ]
        self.assertGreater(
            len(edges), 0,
            "No INDIRECT edge from RETURN to PARAM (expected from state-machine chain)",
        )

    def test_indirect_edges_cross_functions(self):
        """INDIRECT edges connect nodes in different functions by definition."""
        for edge in self.indirect_edges:
            self.assertNotEqual(
                edge.source.object_fn,
                edge.sink.object_fn,
                f"INDIRECT edge {edge} must cross a function boundary",
            )

    def test_function_chain_direction(self):
        """Function1 RETURN → Function2 PARAM, matching the state machine order."""
        fn1 = next(f for f in self.graph.functions if f.name == "Function1")
        fn2 = next(f for f in self.graph.functions if f.name == "Function2")
        chain_edges = [
            e for e in self.indirect_edges
            if e.source.object_fn == fn1 and e.sink.object_fn == fn2
        ]
        self.assertEqual(
            len(chain_edges), 1,
            "Expected exactly one INDIRECT edge from Function1 to Function2",
        )

    def test_indirect_edge_nodes_in_graph(self):
        node_set = set(self.graph.nodes)
        for edge in self.indirect_edges:
            self.assertIn(edge.source, node_set)
            self.assertIn(edge.sink, node_set)


if __name__ == "__main__":
    unittest.main(verbosity=2)
