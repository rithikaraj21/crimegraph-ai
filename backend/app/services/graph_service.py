import hashlib
import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.config import settings

logger = logging.getLogger(__name__)

DEMO_GRAPH_STORE: Dict[str, Dict[str, Any]] = {
    "CASE_2026_094": {
        "case": {
            "case_id": "CASE_2026_094",
            "title": "Operation Blackout Syndicate",
            "description": "Multi-source digital evidence investigation.",
            "status": "ACTIVE",
            "created_at": "2026-10-01T09:00:00+00:00",
        },
        "nodes": [
            {"id": "CASE_2026_094", "label": "Op Blackout Syndicate", "type": "CrimeCase", "properties": {"status": "ACTIVE_INVESTIGATION", "priority": "CRITICAL"}},
            {"id": "PER_01", "label": "John Mercer", "type": "Person", "properties": {"role": "Primary Syndicate Leader", "threat_level": "HIGH"}},
            {"id": "PER_02", "label": "Marcus Vance", "type": "Person", "properties": {"role": "Technical Operator / Botmaster", "threat_level": "CRITICAL"}},
            {"id": "PER_03", "label": "Elena Rostova", "type": "Person", "properties": {"role": "Financial Money Mule", "threat_level": "MEDIUM"}},
            {"id": "PHO_01", "label": "+44 7911 123456", "type": "Phone", "properties": {"carrier": "Encrypted VoIP", "country": "UK"}},
            {"id": "PHO_02", "label": "+44 7922 987654", "type": "Phone", "properties": {"carrier": "Burner SIM", "country": "UK"}},
            {"id": "IP_01", "label": "198.51.100.22", "type": "IPAddress", "properties": {"flagged_by": "Hybrid CNN-LSTM", "status": "MALICIOUS_C2_HOST", "threat_score": 0.984}},
            {"id": "IP_02", "label": "192.168.1.105", "type": "IPAddress", "properties": {"flagged_by": "Hybrid CNN-LSTM", "status": "INFECTED_INTERNAL_BOT"}},
            {"id": "LOC_01", "label": "Central Station Terminal", "type": "Location", "properties": {"city": "London", "significance": "Physical Meeting Point"}},
            {"id": "FILE_01", "label": "carved_payload_01.bin", "type": "EvidenceFile", "properties": {"detected_by": "MLP Classifier", "type": "EXECUTABLE_PAYLOAD", "confidence": 0.9992}},
        ],
        "edges": [
            {"id": "E1", "source": "PER_01", "target": "CASE_2026_094", "relation": "SUSPECT_IN", "confidence": 1.0},
            {"id": "E2", "source": "PER_02", "target": "CASE_2026_094", "relation": "SUSPECT_IN", "confidence": 1.0},
            {"id": "E3", "source": "PER_03", "target": "CASE_2026_094", "relation": "ASSOCIATE_IN", "confidence": 0.85},
            {"id": "E4", "source": "PER_01", "target": "PHO_01", "relation": "OWNS_PHONE", "confidence": 0.95},
            {"id": "E5", "source": "PER_02", "target": "PHO_02", "relation": "OWNS_PHONE", "confidence": 0.95},
            {"id": "E6", "source": "PHO_01", "target": "PHO_02", "relation": "CALL_LOG_RECORD", "confidence": 0.99, "properties": {"calls_count": 14, "total_duration": "42 mins"}},
            {"id": "E7", "source": "PER_01", "target": "LOC_01", "relation": "VISITED", "confidence": 0.92},
            {"id": "E8", "source": "PER_02", "target": "LOC_01", "relation": "VISITED", "confidence": 0.92},
            {"id": "E9", "source": "PER_02", "target": "IP_02", "relation": "OPERATES_DEVICE", "confidence": 0.94},
            {"id": "E10", "source": "IP_02", "target": "IP_01", "relation": "MALICIOUS_BOTNET_COMMUNICATION", "confidence": 0.984, "properties": {"detected_by": "Paper 8 CNN-LSTM"}},
            {"id": "E11", "source": "PER_02", "target": "FILE_01", "relation": "SEIZED_STORAGE_EVIDENCE", "confidence": 0.999},
        ],
    }
}

DEFAULT_CASES = deepcopy(DEMO_GRAPH_STORE)


class GraphService:
    """Owns SQLite-backed case metadata and graph mutations."""

    _initialized = False
    _initialization_lock = threading.Lock()

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return
        with cls._initialization_lock:
            if cls._initialized:
                return
            os.makedirs(os.path.dirname(settings.DATABASE_PATH) or ".", exist_ok=True)
            with cls._connect() as connection:
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS cases (
                        case_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS graph_nodes (
                        case_id TEXT NOT NULL,
                        id TEXT NOT NULL,
                        label TEXT NOT NULL,
                        type TEXT NOT NULL,
                        properties TEXT NOT NULL DEFAULT '{}',
                        PRIMARY KEY (case_id, id),
                        UNIQUE (case_id, type, label COLLATE NOCASE),
                        FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS graph_edges (
                        case_id TEXT NOT NULL,
                        id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        target TEXT NOT NULL,
                        relation TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        properties TEXT NOT NULL DEFAULT '{}',
                        PRIMARY KEY (case_id, id),
                        UNIQUE (case_id, source, target, relation),
                        FOREIGN KEY (case_id, source) REFERENCES graph_nodes(case_id, id) ON DELETE CASCADE,
                        FOREIGN KEY (case_id, target) REFERENCES graph_nodes(case_id, id) ON DELETE CASCADE
                    );
                """)
                existing = connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
                if existing == 0:
                    for case_id, record in deepcopy(DEFAULT_CASES).items():
                        cls._write_case(connection, case_id, record)
                cls._load_cases(connection)
            cls._initialized = True

    @staticmethod
    @contextmanager
    def _connect():
        connection = sqlite3.connect(settings.DATABASE_PATH, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @classmethod
    def _load_cases(cls, connection):
        DEMO_GRAPH_STORE.clear()
        for case in connection.execute("SELECT * FROM cases"):
            nodes = [{
                "id": row["id"],
                "label": row["label"],
                "type": row["type"],
                "properties": json.loads(row["properties"]),
            } for row in connection.execute("SELECT * FROM graph_nodes WHERE case_id = ?", (case["case_id"],))]
            edges = [{
                "id": row["id"],
                "source": row["source"],
                "target": row["target"],
                "relation": row["relation"],
                "confidence": row["confidence"],
                "properties": json.loads(row["properties"]),
            } for row in connection.execute("SELECT * FROM graph_edges WHERE case_id = ?", (case["case_id"],))]
            DEMO_GRAPH_STORE[case["case_id"]] = {
                "case": {
                    "case_id": case["case_id"],
                    "title": case["title"],
                    "description": case["description"],
                    "status": case["status"],
                    "created_at": case["created_at"],
                },
                "nodes": nodes,
                "edges": edges,
            }

    @staticmethod
    def _write_case(connection, case_id, record):
        metadata = record["case"]
        connection.execute(
            """INSERT OR REPLACE INTO cases (case_id, title, description, status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (case_id, metadata["title"], metadata.get("description", ""), metadata["status"], metadata["created_at"]),
        )
        connection.execute("DELETE FROM graph_edges WHERE case_id = ?", (case_id,))
        connection.execute("DELETE FROM graph_nodes WHERE case_id = ?", (case_id,))
        connection.executemany(
            """INSERT INTO graph_nodes (case_id, id, label, type, properties)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (case_id, node["id"], node["label"], node["type"], json.dumps(node.get("properties", {}), default=str))
                for node in record["nodes"]
            ],
        )
        connection.executemany(
            """INSERT INTO graph_edges (case_id, id, source, target, relation, confidence, properties)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (case_id, edge["id"], edge["source"], edge["target"], edge["relation"],
                 edge.get("confidence", 1.0), json.dumps(edge.get("properties", {}), default=str))
                for edge in record["edges"]
            ],
        )

    @classmethod
    def _persist_case(cls, case_id):
        with cls._connect() as connection:
            cls._write_case(connection, case_id, DEMO_GRAPH_STORE[case_id])

    @classmethod
    def list_cases(cls) -> List[Dict[str, Any]]:
        cls.initialize()
        cases = []
        for case_id, record in DEMO_GRAPH_STORE.items():
            graph = record
            metadata = graph["case"]
            cases.append({
                **metadata,
                "total_nodes": len(graph["nodes"]),
                "total_edges": len(graph["edges"]),
            })
        return sorted(cases, key=lambda case: case["created_at"], reverse=True)

    @classmethod
    def create_case(cls, case_id: str, title: str, description: str = "") -> Dict[str, Any]:
        cls.initialize()
        if case_id in DEMO_GRAPH_STORE:
            raise ValueError(f"Case '{case_id}' already exists.")
        metadata = {
            "case_id": case_id,
            "title": title.strip(),
            "description": description.strip(),
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        DEMO_GRAPH_STORE[case_id] = {
            "case": metadata,
            "nodes": [{
                "id": case_id,
                "label": title.strip(),
                "type": "CrimeCase",
                "properties": {"status": "ACTIVE_INVESTIGATION", "description": description.strip()},
            }],
            "edges": [],
        }
        try:
            cls._persist_case(case_id)
        except Exception:
            del DEMO_GRAPH_STORE[case_id]
            raise
        return {**metadata, "total_nodes": 1, "total_edges": 0}

    @classmethod
    def get_case_graph(cls, case_id: str) -> Dict[str, Any]:
        cls.initialize()
        if case_id not in DEMO_GRAPH_STORE:
            raise KeyError(f"Case '{case_id}' was not found.")

        case_data = DEMO_GRAPH_STORE[case_id]
        return {
            "case_id": case_id,
            "nodes": case_data["nodes"],
            "edges": case_data["edges"],
            "total_nodes": len(case_data["nodes"]),
            "total_edges": len(case_data["edges"]),
        }

    @classmethod
    def add_extracted_entities(cls, case_id: str, extracted_data: Dict[str, Any]):
        cls.initialize()
        if case_id not in DEMO_GRAPH_STORE:
            raise KeyError(f"Case '{case_id}' was not found.")

        graph = deepcopy(DEMO_GRAPH_STORE[case_id])
        existing_by_key = {
            (node["type"], node["label"].casefold()): node["id"]
            for node in graph["nodes"]
        }
        existing_by_id = {node["id"]: node for node in graph["nodes"]}
        id_map: Dict[str, str] = {}
        for node in extracted_data.get("nodes", []):
            if not {"id", "label", "type"}.issubset(node):
                continue
            key = (str(node["type"]), str(node["label"]).casefold())
            node_id = case_id if str(node["id"]) == case_id and node["type"] == "CrimeCase" else existing_by_key.get(key)
            if node_id is None:
                node_id = str(node["id"])
                existing = existing_by_id.get(node_id)
                if existing and (existing["type"], existing["label"].casefold()) != key:
                    node_id = _stable_id(case_id, *key)
                while node_id in existing_by_id and (existing_by_id[node_id]["type"], existing_by_id[node_id]["label"].casefold()) != key:
                    node_id = _stable_id(case_id, node_id, *key)
            id_map[str(node["id"])] = node_id
            if node_id in existing_by_id:
                for stored_node in graph["nodes"]:
                    if stored_node["id"] == node_id:
                        stored_node["properties"].update(node.get("properties", {}))
                        break
            else:
                new_node = {
                    "id": node_id,
                    "label": str(node["label"]),
                    "type": str(node["type"]),
                    "properties": node.get("properties", {}),
                }
                graph["nodes"].append(new_node)
                existing_by_id[node_id] = new_node
                existing_by_key[key] = node_id

        existing_edges = {
            (edge["source"], edge["target"], edge["relation"])
            for edge in graph["edges"]
        }
        known_nodes = {node["id"] for node in graph["nodes"]}
        for edge in extracted_data.get("relationships", []):
            source = id_map.get(str(edge.get("source")), str(edge.get("source", "")))
            target = id_map.get(str(edge.get("target")), str(edge.get("target", "")))
            relation = str(edge.get("relation", "RELATED_TO"))
            if source not in known_nodes or target not in known_nodes:
                continue
            edge_key = (source, target, relation)
            if edge_key in existing_edges:
                continue
            graph["edges"].append({
                "id": _stable_id(case_id, source, target, relation),
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": max(0.0, min(1.0, float(edge.get("confidence", 1.0)))),
                "properties": edge.get("properties", {}),
            })
            existing_edges.add(edge_key)
        try:
            with cls._connect() as connection:
                cls._write_case(connection, case_id, graph)
        except Exception:
            logger.exception("Could not persist graph updates for case %s", case_id)
            raise
        DEMO_GRAPH_STORE[case_id] = graph
        return graph

    @classmethod
    def add_traffic_result(cls, case_id: str, result: Dict[str, Any]):
        cls._require_case(case_id)
        src_id = _stable_id("IPAddress", result["src_ip"])
        dst_id = _stable_id("IPAddress", result["dst_ip"])
        cls.add_extracted_entities(case_id, {
            "nodes": [
                {"id": src_id, "label": result["src_ip"], "type": "IPAddress", "properties": {"evidence_source": "CNN-LSTM traffic analysis"}},
                {"id": dst_id, "label": result["dst_ip"], "type": "IPAddress", "properties": {"evidence_source": "CNN-LSTM traffic analysis"}},
            ],
            "relationships": [
                {"source": src_id, "target": dst_id, "relation": result["classification"], "confidence": result["confidence"], "properties": {"duration": result["duration"], "bytes": result["total_bytes"], "threat_score": result["threat_score"], "model": result["model"]}},
                {"source": src_id, "target": case_id, "relation": "OBSERVED_IN_CASE", "confidence": 1.0},
                {"source": dst_id, "target": case_id, "relation": "OBSERVED_IN_CASE", "confidence": 1.0},
            ],
        })
        return DEMO_GRAPH_STORE[case_id]

    @classmethod
    def add_file_result(cls, case_id: str, result: Dict[str, Any]):
        cls._require_case(case_id)
        file_id = _stable_id("EvidenceFile", case_id, result["file_name"])
        cls.add_extracted_entities(case_id, {
            "nodes": [{
                "id": file_id,
                "label": result["file_name"],
                "type": "EvidenceFile",
                "properties": {
                    "classified_type": result["predicted_file_type"],
                    "confidence": result["confidence"],
                    "diagnostic_signatures": result["diagnostic_signatures"],
                    "evidence_source": result["model"],
                },
            }],
            "relationships": [{
                "source": file_id,
                "target": case_id,
                "relation": "EVIDENCE_IN_CASE",
                "confidence": result["confidence"],
            }],
        })
        return DEMO_GRAPH_STORE[case_id]

    @classmethod
    def _require_case(cls, case_id: str):
        cls.initialize()
        if case_id not in DEMO_GRAPH_STORE:
            raise KeyError(f"Case '{case_id}' was not found.")
        return DEMO_GRAPH_STORE[case_id]


def _stable_id(*parts: Any) -> str:
    value = "|".join(str(part) for part in parts)
    return "ENT_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
