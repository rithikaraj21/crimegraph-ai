# CrimeGraph AI 🔍🕸️
**An AI-Assisted Digital Investigation & Graph Analytics System**

---

## 1. Project Overview

**CrimeGraph AI** is an intelligent investigation-support platform designed to assist law enforcement, digital forensics analysts, and fraud investigators in connecting disparate case information. 

Real-world investigations generate heterogeneous data across multiple modalities: suspect profiles, phone logs, digital evidence files, network traffic captures, financial transactions, incident locations, and narrative police reports. CrimeGraph AI extracts, links, and visually maps these entities into a unified knowledge graph.

> **Important Disclaimer:** CrimeGraph AI is an **investigation-support tool**. It does not declare guilt, infer intent, or predict criminality; rather, it empowers human investigators to discover hidden relationships, identify high-centrality nodes, and explore evidentiary trails objectively.

```
┌──────────────────┐     ┌───────────────────────┐     ┌──────────────────────┐
│  Case Information│ ──► │  AI Extraction Engine │ ──► │     Neo4j Graph      │
│(Docs, Logs, Pcap)│     │(LLM + CNN/LSTM + MLP) │     │ (Entities & Relations│
└──────────────────┘     └───────────────────────┘     └──────────┬───────────┘
                                                                  │
┌──────────────────┐     ┌───────────────────────┐                │
│ Case Summary &   │ ◄── │ Interactive Discovery │ ◄──────────────┘
│ Evidence Briefing│     │ (Cytoscape / Filters) │
└──────────────────┘     └───────────────────────┘
```

---

## 2. Core Architecture & Workflow

1. **Multimodal Ingestion & Feature Extraction:**
   - **Case Dossiers & Text Reports:** Ingested via an LLM API with structured schema extraction to extract POLE (Persons, Objects, Locations, Events) entities and relationships.
   - **Digital Evidence Files:** Ingested via an Explainable MLP classifier (with TF-IDF and SHAP/LIME) to classify file types and metadata.
   - **Network Traffic & Botnet Logs:** Analyzed via a deep CNN-LSTM hybrid model to flag malicious IP addresses, C2 traffic, and botnet activity.
2. **Graph Storage & Knowledge Representation:**
   - Entities (People, Phone Numbers, IP Addresses, Files, Locations, Incidents) and Edges (CALLED, ASSOCIATED_WITH, COMMUNICATED_TO, LOCATED_AT, OWNS) are persisted in **Neo4j**.
3. **Investigator Interface:**
   - An interactive React dashboard powered by **Cytoscape.js** for visual link analysis, graph centrality analysis, timeline filtering, and node expansion.
4. **AI Case Briefing:**
   - Summarization engine produces auditable investigative reports explaining the discovered connections and evidentiary weight.

---

## 3. Datasets

| Dataset | Source / Reference | Role in CrimeGraph AI | Nature | Status |
|---|---|---|---|---|
| **Govdocs1** | Paper 5 | Training file-type classification models for digital evidence files | Real | Subset downloaded |
| **CTU-13 / IoT-23** | Paper 8 | Network traffic captures for botnet & malicious IP detection | Real | NetFlow/subset in progress |
| **data.police.uk** | Public Police Portal | Real-world crime incident types, timestamps, and geolocation points | Real | Acquired |
| **POLE Manchester** | Forensic Benchmark | Schema benchmark for Persons, Objects, Locations, and Events | Real crime / synthetic identities | Acquired |
| **Synthetic Dossiers** | Papers 1, 2, 3, 7, 9, 10 | Benchmark case reports, phone records, accounts, and ground truth labels | Synthetic | Generated & verified |

---

## 4. Machine Learning & AI Models

| Model | Architecture | Dataset | Primary Role & Output |
|---|---|---|---|
| **Malicious Traffic Detector** | **CNN + LSTM Hybrid**<br>*(Spatial feature extraction + Temporal sequence analysis)* | CTU-13 / IoT-23 | Flags malicious network flows; links suspicious IP and device nodes directly into the graph. |
| **Evidence File Classifier** | **MLP with TF-IDF**<br>*(Baseline: Random Forest; Explainability: SHAP / LIME)* | Govdocs1 | Classifies digital file fragments and evidence types; assigns explainability weights to evidence nodes. |
| **Entity & Relation Extractor** | **Pretrained LLM API**<br>*(Gemini 2.0 Flash with Structured Outputs)* | Case narratives & reports | Zero/Few-shot extraction of Persons, Phones, Locations, and Relationships into validated JSON graphs. |

> **Note on Paper 8 (CNN + LSTM):** Technically designed as a **single hybrid end-to-end architecture** (CNN extracts spatial flow features; LSTM learns temporal transitions). For evaluation and viva benchmarks, baseline comparisons against standalone CNN and standalone LSTM are reported.

---

## 5. Technology Stack

| Layer | Selected Technology | Rationale |
|---|---|---|
| **Backend API** | **FastAPI (Python)** | Asynchronous support for streaming LLM calls, native Pydantic schema validation for graph payloads, and automatic Swagger docs (`/docs`). |
| **Frontend UI** | **React + Vite + Cytoscape.js** | Industry standard for forensic network graphs, responsive node physics, layout algorithms (CoSE/Cola), and fast investigator UX. |
| **Graph Database** | **Neo4j (Docker / Neo4j Aura)** | High-performance labeled property graph (LPG), Cypher query language, and graph data science (GDS) algorithms. |
| **LLM Provider** | **Google Gemini 2.0 Flash API** | Massive 1M token context for long case files, native structured JSON schema enforcement, and cost-effective latency. |
| **ML Training** | **PyTorch / Scikit-learn on Google Colab (GPU)** | Accelerated GPU training for deep CNN-LSTM and SHAP/LIME explainability calculations. |
| **Version Control** | **GitHub + VS Code** | Collaborative development, issue tracking, and clean modular code structure. |

---

## 6. Directory Structure (Proposed)

```text
crimegraphai/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route controllers
│   │   ├── core/            # Config, Neo4j driver connection
│   │   ├── services/        # LLM extractor, Cypher builder, graph services
│   │   ├── schemas/         # Pydantic schemas (Node, Edge, Case)
│   │   └── main.py          # FastAPI application entrypoint
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Graph canvas (Cytoscape), Timeline, Dossier panel
│   │   ├── hooks/           # Graph queries & state
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── models/
│   ├── botnet_cnn_lstm/     # Colab training scripts & weights for CTU-13/IoT-23
│   └── file_classifier_mlp/ # MLP + TF-IDF + SHAP/LIME scripts for Govdocs1
├── data/
│   ├── samples/             # Sample cases and benchmark POLE schemas
│   └── synthetic_gen/       # Case dossier generator scripts
└── README.md
```

---

## 7. Next Steps & Milestones

- [x] Settle project scope, datasets, and architectural foundations.
- [ ] Confirm hybrid CNN-LSTM evaluation plan with guide/faculty.
- [ ] Initialize FastAPI backend and connect to Neo4j instance.
- [ ] Implement Gemini API extraction pipeline with structured JSON schema.
- [ ] Build Cytoscape.js React graph interface for node expansion and inspection.
- [ ] Train and export CNN-LSTM and MLP model weights from Google Colab.
