# Evidence File-Type Classifier with Explainability (Paper 5)

This directory contains the implementation, baseline benchmarking, and explainability artifacts for the **Digital Evidence File-Type Classification Model** based on **Paper 5** for CrimeGraph AI.

---

## 1. Overview & Objective

* **Primary Objective:** Analyze raw byte streams, carved forensic file fragments, and headerless/renamed files recovered from seized storage devices to identify true file formats and prevent evidence obfuscation.
* **Architecture:**
  * **Feature Extraction:** Sublinear TF-IDF vectorization over byte hex n-grams ($\text{ngram\_range}=(1, 2)$, top 500 features).
  * **Baseline Model:** Random Forest Classifier ($100$ estimators, $\text{max\_depth}=20$).
  * **Proposed Model:** Multi-Layer Perceptron (`MLPClassifier` with $[128, 64]$ hidden layers, early stopping).
* **Explainability:** The training utilities include SHAP analysis. The web app reports recognized file-header signatures as diagnostic context; these signatures are not SHAP explanations and do not prove a file's origin.
* **Application Integration:** The FastAPI service stores an `EvidenceFile` node, its classification, confidence, and case relationship in SQLite.

---

## 2. Experimental Benchmark Results (Tabular Metrics)

Evaluated on a strictly held-out test split ($20\%$, $1,200$ samples) across $6$ forensic file categories: `PDF_DOCUMENT`, `OFFICE_DOCX`, `JPEG_IMAGE`, `EXECUTABLE_PAYLOAD`, `TEXT_LOG`, and `ARCHIVE_ZIP`.

| Model Name | Role in Paper 5 | Dataset | Accuracy | Weighted Precision | Weighted Recall | Weighted F1-Score | Macro F1-Score | Training Time (s) | Explainability Engine |
|---|---|---|---|---|---|---|---|---|---|
| **Random Forest** | Baseline Model | Govdocs1 Fragments | 99.92% | 99.92% | 99.92% | 0.9992 | 0.9992 | ~2.50 s | SHAP TreeExplainer |
| **MLP Classifier (Proposed)** | Primary Model | Govdocs1 Fragments | **99.92%** | **99.92%** | **99.92%** | **0.9992** | **0.9992** | **~2.79 s** | SHAP Feature Attribution |

### Per-Category Performance Breakdown (Proposed MLP)

| Forensic File Class | Representative Signature / Magic Bytes | Precision | Recall | F1-Score | Test Support |
|---|---|---|---|---|---|
| `PDF_DOCUMENT` | `25 50 44 46 2d` (`%PDF-`), `obj / endobj` | 1.0000 | 1.0000 | 1.0000 | 200 |
| `OFFICE_DOCX` | `50 4b 03 04`, `word/document.xml` | 0.9950 | 1.0000 | 0.9975 | 200 |
| `JPEG_IMAGE` | `ff d8 ff e0` (SOI / JFIF), `ff d9` (EOI) | 1.0000 | 1.0000 | 1.0000 | 200 |
| `EXECUTABLE_PAYLOAD` | `4d 5a` (`MZ`), `7f 45 4c 46` (`ELF`), `.text` | 1.0000 | 0.9950 | 0.9975 | 200 |
| `TEXT_LOG` | `[INFO]`, `AUTH_FAIL`, `USER_LOGIN` | 1.0000 | 1.0000 | 1.0000 | 200 |
| `ARCHIVE_ZIP` | `50 4b 03 04`, `50 4b 01 02` (Central Dir) | 1.0000 | 1.0000 | 1.0000 | 200 |
| **Overall Macro Average** | — | **0.9992** | **0.9992** | **0.9992** | **1,200** |

---

## 3. Directory Layout & Artifacts

| File / Folder | Purpose |
|---|---|
| `dataset.py` | Forensic fragment synthesizer & raw Govdocs1 binary chunk parser. |
| `model.py` | Pipeline encapsulating `TfidfVectorizer`, `RandomForestClassifier`, and `MLPClassifier`. |
| `train.py` | Model fitting, baseline evaluation matrix generation, and SHAP Shapley computation. |
| `explainability.py` | Standalone research helper for feature attributions and graph-query examples; the web app uses `backend/app/services/ml_service.py` instead. |
| `saved_models/mlp_classifier.joblib` | Serialized trained MLP neural network model. |
| `saved_models/rf_baseline.joblib` | Serialized baseline Random Forest model. |
| `saved_models/tfidf_vectorizer.joblib` | Fitted TF-IDF vocabulary and n-gram weights. |
| `saved_models/model_comparison.json` | Quantitative comparison metrics report. |
| `saved_models/shap_summary.png` | Feature attribution plot showing top forensic signatures. |

---

## 4. Execution Commands

```powershell
# Train both Baseline and MLP, compute metrics, and generate SHAP plots
& "d:\crimegraphai\.venv\Scripts\python.exe" d:\crimegraphai\models\file_classifier_mlp\train.py

# Run explainable inference on an evidence file fragment
& "d:\crimegraphai\.venv\Scripts\python.exe" d:\crimegraphai\models\file_classifier_mlp\explainability.py
```
