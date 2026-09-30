# CrimeGraph AI - AI-Assisted Digital Investigation System

Case information -> AI extracts entities and relationships -> Neo4j stores a graph -> investigator explores connections -> AI summarises the case.

CrimeGraph AI is an **investigation-support tool**. It does not declare anyone guilty or predict who committed a crime.

## Repository layout
| Path | Content |
|---|---|
| `papers/` | The 10 reference papers (reference list, not PDFs) |
| `datasets/` | Dataset inventory, synthetic dataset, instructions for public datasets |
| `datasets/synthetic/` | Our fictional investigation dataset, generator, Neo4j loader, demo queries |
| `scripts/` | Download script for public datasets |

## Quick start (synthetic dataset)
    cd datasets/synthetic
    docker compose up -d
    pip install neo4j
    python load_to_neo4j.py --reset
Open http://localhost:7474 (neo4j / crimegraph123) and run `queries.cypher`.

See `datasets/README.md` for every dataset, its source, licence and status.

## Team
TODO: names
