# CrimeGraph AI

CrimeGraph AI is a project that uses AI and Neo4j to help in crime investigation.

The main idea is to take crime data, convert it into a graph, find relationships
between different crime details and give useful information to the investigator.

## Datasets

### 1. data.police.uk

This is our main dataset.

Source:
https://data.police.uk/data/

It contains public crime data such as:

- Crime ID
- Month
- Crime type
- Location
- Latitude
- Longitude
- LSOA
- Police force
- Crime outcome

We use this data to create our main crime graph.

---

### 2. POLE Manchester

Source:
https://github.com/neo4j-graph-examples/pole

POLE means:

- Person
- Object
- Location
- Event

We use the POLE project as a reference for creating our crime investigation
graph in Neo4j.

It helps us understand how different investigation information can be
connected.

---

### 3. Govdocs1 / Garfinkel Dataset

Source:
https://digitalcorpora.org/corpora/file-corpora/files/

This dataset is used for the digital forensics part of our project.

We use it to work with digital files and evidence.

It is related to the paper:

**SIFT: Sifting file types - application of explainable artificial
intelligence in cyber forensics**

DOI:
https://doi.org/10.1186/s42400-024-00241-9

---

### 4. Synthetic CrimeGraph Dataset

We also create our own small synthetic dataset.

It contains fictional investigation information such as:

- Person
- Device
- Event
- Evidence
- Crime

This is only for testing and showing relationships in our system.

It is not real police data.

## How the project works

```text
Crime Data
    ↓
Python
    ↓
Data Cleaning
    ↓
Neo4j
    ↓
Crime Knowledge Graph
    ↓
Pattern / Relationship Analysis
    ↓
AI
    ↓
React Dashboard
