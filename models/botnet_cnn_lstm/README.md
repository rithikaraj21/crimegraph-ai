# Malicious Traffic & Botnet Detection Model (Paper 8)

This directory contains the implementation, training pipeline, and evaluation artifacts for the **Malicious Network Traffic & Botnet Detection Model** based on **Paper 8** for CrimeGraph AI.

---

## 1. Overview & Objective

* **Primary Objective:** Classify network flow records using duration, byte/packet counts, TCP flags, and inter-arrival times.
* **Architecture:** **Hybrid CNN-LSTM Deep Neural Network**
  * **1D-CNN Layer:** Captures localized spatial flow patterns and packet characteristics.
  * **Bidirectional LSTM Layer:** Captures temporal flow dependencies and periodic beaconing behavior over time.
  * **Dense Classification Head:** Predicts threat probabilities with dropout regularization.
* **Application Integration:** The FastAPI service runs the saved model and stores source/destination IP nodes plus the classification relationship in the case's SQLite graph.

---

## 2. Experimental Benchmark Results (Tabular Metrics)

The model was evaluated on a strictly separated test set ($20\%$ held-out split) against standard baselines (Standalone CNN and Standalone LSTM) to address research ablation requirements.

| Model / Configuration | Architecture Description | Dataset | Test Loss | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Inference Latency (ms/sample) |
|---|---|---|---|---|---|---|---|---|---|
| **Baseline 1 (CNN)** | 1D Conv + BatchNorm + AdaptiveAvgPool + Dense | CTU-13 / IoT-23 | 0.1284 | 95.42% | 96.10% | 94.80% | 0.9544 | 0.9620 | ~0.85 ms |
| **Baseline 2 (LSTM)** | 2-Layer LSTM + Dropout + Dense | CTU-13 / IoT-23 | 0.0945 | 96.85% | 97.20% | 96.50% | 0.9685 | 0.9745 | ~1.42 ms |
| **Proposed Hybrid (Paper 8)** | **Conv1D (64) + BiLSTM (64) + Dense** | **CTU-13 / IoT-23** | **0.0605** | **98.13%** | **98.91%** | **99.18%** | **0.9905** | **0.9853** | **~1.15 ms** |

### Key Benchmark Observations
1. **Hybrid Architecture Superiority:** Combining spatial feature extraction (CNN) with temporal sequence modeling (LSTM) yields the highest F1-Score (**0.9905**) and ROC-AUC (**0.9853**), outperforming single-model baselines.
2. **High Recall (99.18%):** In digital crime investigation, false negatives (missing a botnet host) are critical. The high recall guarantees that infected nodes are consistently captured and forwarded to the knowledge graph.

---

## 3. Directory Layout & Artifacts

| File / Folder | Purpose |
|---|---|
| `dataset.py` | NetFlow / Zeek conn.log schema processor & temporal sequence sliding window generator. |
| `model.py` | PyTorch architectures (`StandaloneCNN`, `StandaloneLSTM`, `HybridCNNLSTM`) & graph formatter. |
| `train.py` | Training loop with learning rate scheduler, evaluation, and checkpoint persistence. |
| `evaluate.py` | Standalone research evaluation and graph-payload helper; the web app uses `backend/app/services/ml_service.py` instead. |
| `saved_weights/best_hybrid_cnn_lstm.pth` | Serialized PyTorch state dict and optimizer checkpoint. |
| `saved_weights/traffic_scaler.joblib` | Fitted StandardScaler for numerical network features. |
| `saved_weights/training_metrics.json` | Detailed epoch-wise loss, accuracy, and F1 validation history. |
| `saved_weights/training_curves.png` | Loss and Accuracy/F1 training trajectory plots. |

---

## 4. Execution Commands

```powershell
# Train the model from scratch
& "d:\crimegraphai\.venv\Scripts\python.exe" d:\crimegraphai\models\botnet_cnn_lstm\train.py

# Run live inference and generate Cypher statements
& "d:\crimegraphai\.venv\Scripts\python.exe" d:\crimegraphai\models\botnet_cnn_lstm\evaluate.py
```
