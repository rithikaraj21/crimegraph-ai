#!/usr/bin/env python3
"""
Load the CrimeGraph synthetic dataset (./csv) into Neo4j.

    pip install neo4j
    python load_to_neo4j.py --reset                 # wipe DB, then load
    python load_to_neo4j.py --dry-run               # build all batches, touch no database

Connection (env vars, defaults match docker-compose.yml):
    NEO4J_URI=bolt://localhost:7687  NEO4J_USER=neo4j  NEO4J_PASSWORD=crimegraph123
Every node gets the label :Entity plus its own label; ids are unique across :Entity.
"""
import argparse, csv, os
from datetime import datetime, date

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv")


def rows(name):
    with open(os.path.join(CSV, name), encoding="utf-8", newline="") as f:
        return [{k: (v if v != "" else None) for k, v in r.items()} for r in csv.DictReader(f)]


dt = lambda v: datetime.fromisoformat(v) if v else None
d_ = lambda v: date.fromisoformat(v) if v else None
i_ = lambda v: int(v) if v else None
f_ = lambda v: float(v) if v else None
s_ = lambda v: v

# file, label, id column, {property: (column, cast)}
NODES = [
    ("persons.csv", "Person", "person_id", {"name": ("name", s_), "role": ("role", s_), "alias": ("alias", s_)}),
    ("devices.csv", "Device", "device_id", {"name": ("identifier", s_), "device_type": ("device_type", s_),
                                            "description": ("description", s_)}),
    ("locations.csv", "Location", "location_id", {"name": ("name", s_), "latitude": ("latitude", f_),
                                                  "longitude": ("longitude", f_), "location_type": ("location_type", s_)}),
    ("cases.csv", "Case", "case_id", {"name": ("title", s_), "status": ("status", s_), "opened": ("opened_date", d_)}),
    ("incidents.csv", "Incident", "incident_id", {"name": ("type", s_), "type": ("type", s_), "datetime": ("datetime", dt),
                                                  "summary": ("summary", s_)}),
    ("accounts.csv", "Account", "account_id", {"name": ("account_no_masked", s_), "bank": ("bank", s_)}),
    ("evidence.csv", "Evidence", "evidence_id", {"name": ("evidence_type", s_), "evidence_type": ("evidence_type", s_),
                                                 "description": ("description", s_), "collected": ("collected_date", d_)}),
    ("ip_addresses.csv", "IPAddress", "ip_id", {"name": ("address", s_), "threat_label": ("label", s_)}),
    ("reports.csv", "CaseReport", "report_id", {"name": ("title", s_), "report_type": ("report_type", s_),
                                                "date": ("date", d_), "file": ("file", s_)}),
]
# relationships from a single generic table
GENERIC_TYPES = ["USES", "OWNS", "VICTIM_OF", "WITNESSED", "VISITED", "OCCURRED_AT", "PART_OF", "CONTACTED",
                 "ASSOCIATED_WITH", "SUPPORTS", "FOUND_ON", "DERIVED_FROM", "MENTIONS", "PROVIDED"]


def build_batches():
    batches = []  # (label_for_report, cypher, rows)
    for fname, label, idc, props in NODES:
        data = []
        for r in rows(fname):
            p = {k: c(r[col]) for k, (col, c) in props.items()}
            if label == "Incident":
                p["name"] = f"{r['incident_id']} {r['type']}"
            if label == "Evidence":
                p["name"] = f"{r['evidence_id']} {r['evidence_type']}"
            data.append(dict(id=r[idc], props={k: v for k, v in p.items() if v is not None}))
        batches.append((label, f"UNWIND $rows AS row MERGE (n:Entity {{id: row.id}}) SET n:{label}, n += row.props", data))

    def rel(label, typ, data):
        q = (f"UNWIND $rows AS row MATCH (a:Entity {{id: row.s}}), (b:Entity {{id: row.t}}) "
             f"MERGE (a)-[r:{typ} {{rid: row.rid}}]->(b) SET r += row.props")
        batches.append((label, q, data))

    g = rows("relationships.csv")
    for typ in GENERIC_TYPES:
        data = []
        for r in g:
            if r["relationship"] != typ:
                continue
            p = {"source_doc": r["source_doc"], "date": d_(r["date"]), "call_count": i_(r["call_count"]),
                 "first_call": d_(r["first_call"]), "last_call": d_(r["last_call"])}
            data.append(dict(s=r["source_id"], t=r["target_id"], rid=r["rel_id"],
                             props={k: v for k, v in p.items() if v is not None}))
        rel(typ, typ, data)
    rel("CALLED", "CALLED", [dict(s=r["caller_device_id"], t=r["callee_device_id"], rid=r["call_id"],
         props={k: v for k, v in dict(timestamp=dt(r["timestamp"]), duration_sec=i_(r["duration_sec"]),
                                      caller_location_id=r["caller_location_id"]).items() if v is not None})
         for r in rows("calls.csv")])
    tx = rows("transactions.csv")
    tprops = lambda r: {k: v for k, v in dict(amount_inr=i_(r["amount_inr"]), timestamp=dt(r["timestamp"]),
                                              channel=r["channel"], txn_id=r["txn_id"],
                                              source_doc=r["source_doc"]).items() if v is not None}
    rel("TRANSFERRED_TO", "TRANSFERRED_TO", [dict(s=r["from_account_id"], t=r["to_account_id"], rid=r["txn_id"],
        props=tprops(r)) for r in tx if r["to_account_id"]])
    rel("WITHDRAWN_AT", "WITHDRAWN_AT", [dict(s=r["from_account_id"], t=r["atm_location_id"], rid=r["txn_id"],
        props=tprops(r)) for r in tx if not r["to_account_id"]])
    rel("CONNECTED_TO", "CONNECTED_TO", [dict(s=r["device_id"], t=r["ip_id"], rid=r["event_id"],
        props={k: v for k, v in dict(timestamp=dt(r["timestamp"]), protocol=r["protocol"], dst_port=i_(r["dst_port"]),
                                     bytes=i_(r["bytes"]), label=r["label"]).items() if v is not None})
        for r in rows("network_events.csv")])
    rel("PART_OF", "PART_OF", [dict(s=r["evidence_id"], t=r["case_id"], rid="PO-" + r["evidence_id"], props={})
                               for r in rows("evidence.csv")])
    rel("ABOUT", "ABOUT", [dict(s=r["report_id"], t=r["case_id"], rid="AB-" + r["report_id"], props={})
                           for r in rows("reports.csv")])
    return batches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete everything first")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    batches = build_batches()
    if a.dry_run:
        for label, _, data in batches:
            print(f"{label:16s} {len(data):5d} rows")
        print("dry run OK - nothing written")
        return
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                               auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "crimegraph123")))
    with drv, drv.session() as s:
        if a.reset:
            s.run("MATCH (n) DETACH DELETE n").consume()
        s.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE").consume()
        for label, q, data in batches:
            s.run(q, rows=data).consume()
            print(f"loaded {label:16s} {len(data):5d}")
        print(s.run("MATCH (n) RETURN count(n) AS nodes").single()["nodes"], "nodes,",
              s.run("MATCH ()-[r]->() RETURN count(r) AS rels").single()["rels"], "relationships")


if __name__ == "__main__":
    main()
