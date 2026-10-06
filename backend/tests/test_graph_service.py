import tempfile
import unittest
from pathlib import Path

from app.core.config import settings
from app.services.graph_service import DEMO_GRAPH_STORE, GraphService
from app.services.llm_service import LLMExtractorService


class GraphServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database_path = settings.DATABASE_PATH
        settings.DATABASE_PATH = str(Path(self.temp_dir.name) / "test.sqlite3")
        GraphService._initialized = False
        DEMO_GRAPH_STORE.clear()
        GraphService.initialize()

    def tearDown(self):
        settings.DATABASE_PATH = self.original_database_path
        GraphService._initialized = False
        DEMO_GRAPH_STORE.clear()
        self.temp_dir.cleanup()

    def test_seed_graph_is_available(self):
        graph = GraphService.get_case_graph("CASE_2026_094")
        self.assertEqual(graph["total_nodes"], 10)
        self.assertEqual(graph["total_edges"], 11)

    def test_new_case_is_created_and_duplicate_is_rejected(self):
        created = GraphService.create_case("CASE_TEST_1", "Test investigation", "A small test case.")
        self.assertEqual(created["total_nodes"], 1)
        self.assertEqual(GraphService.get_case_graph("CASE_TEST_1")["nodes"][0]["label"], "Test investigation")
        with self.assertRaises(ValueError):
            GraphService.create_case("CASE_TEST_1", "Duplicate")

    def test_entity_upsert_deduplicates_nodes_and_relationships(self):
        payload = {
            "nodes": [{"id": "PER_TEMP", "label": "Jordan Example", "type": "Person", "properties": {"role": "witness"}}],
            "relationships": [{"source": "PER_TEMP", "target": "CASE_2026_094", "relation": "MENTIONED_IN", "confidence": 0.8}],
        }
        GraphService.add_extracted_entities("CASE_2026_094", payload)
        graph = GraphService.add_extracted_entities("CASE_2026_094", payload)
        self.assertEqual(sum(node["label"] == "Jordan Example" for node in graph["nodes"]), 1)
        self.assertEqual(sum(edge["relation"] == "MENTIONED_IN" for edge in graph["edges"]), 1)

    def test_extracted_ids_do_not_overwrite_existing_entities(self):
        graph = GraphService.add_extracted_entities("CASE_2026_094", {
            "nodes": [{"id": "PER_01", "label": "New Person", "type": "Person", "properties": {}}],
            "relationships": [{"source": "PER_01", "target": "CASE_2026_094", "relation": "MENTIONED_IN_CASE", "confidence": 0.9}],
        })
        john = next(node for node in graph["nodes"] if node["id"] == "PER_01")
        new_person = next(node for node in graph["nodes"] if node["label"] == "New Person")
        self.assertEqual(john["label"], "John Mercer")
        self.assertNotEqual(new_person["id"], "PER_01")

    def test_graph_updates_survive_service_reinitialization(self):
        GraphService.create_case("CASE_PERSIST", "Persistent case")
        GraphService.add_extracted_entities("CASE_PERSIST", {
            "nodes": [{"id": "IP_TEST", "label": "203.0.113.8", "type": "IPAddress", "properties": {"source": "test"}}],
            "relationships": [{"source": "IP_TEST", "target": "CASE_PERSIST", "relation": "OBSERVED_IN_CASE", "confidence": 1}],
        })
        GraphService._initialized = False
        DEMO_GRAPH_STORE.clear()
        graph = GraphService.get_case_graph("CASE_PERSIST")
        self.assertEqual(graph["total_nodes"], 2)
        self.assertEqual(graph["total_edges"], 1)

    def test_unknown_case_is_not_replaced_with_demo_data(self):
        with self.assertRaises(KeyError):
            GraphService.get_case_graph("CASE_MISSING")

    def test_local_extraction_does_not_invent_person_phone_links(self):
        extracted = LLMExtractorService._fallback_pattern_extractor(
            "Suspect Elena Rostova contacted +44 7933 112233 near Heathrow Airport. Host 999.1.1.1 and 198.51.100.99.",
            "CASE_TEST",
        )
        self.assertTrue(any(node["label"] == "Elena Rostova" for node in extracted["nodes"]))
        self.assertTrue(any(node["label"] == "Heathrow Airport" and node["type"] == "Location" for node in extracted["nodes"]))
        self.assertFalse(any(node["label"] == "999.1.1.1" for node in extracted["nodes"]))
        self.assertFalse(any(edge["relation"] == "OPERATES_PHONE" for edge in extracted["relationships"]))

    def test_narrative_case_node_merges_into_existing_case(self):
        extracted = LLMExtractorService._fallback_pattern_extractor(
            "Suspect Elena Rostova contacted +44 7933 112233 near Heathrow Airport.",
            "CASE_2026_094",
        )
        graph = GraphService.add_extracted_entities("CASE_2026_094", extracted)
        case_nodes = [node for node in graph["nodes"] if node["type"] == "CrimeCase"]
        self.assertEqual(len(case_nodes), 1)
        self.assertTrue(any(edge["target"] == "CASE_2026_094" for edge in graph["edges"]))


if __name__ == "__main__":
    unittest.main()
