# Malicious Traffic & Botnet Detection Model (Paper 8)

This directory contains the implementation, training pipeline, and evaluation artifacts for the **Malicious Network Traffic & Botnet Detection Model** based on **Paper 8** for CrimeGraph AI.

---

## 1. Overview & Objective

* **Primary Objective:** Demonstrate classification of network flow records using duration, byte/packet counts, protocol flags, and inter-arrival times.
* **Architecture:** **Hybrid CNN-LSTM Deep Neural Network**
  * **1D-CNN Layer:** Captures localized spatial flow patterns and packet characteristics.
  * **Bidirectional LSTM Layer:** Captures temporal flow dependencies and periodic beaconing behavior over time.
  * **Dense Classification Head:** Predicts threat probabilities with dropout regularization.
* **Application Integration:** The FastAPI service runs the saved model and stores source/destination IP nodes plus the classification relationship in the case's SQLite graph.

---

## 2. Data and Evaluation

The checked-in training pipeline generates a balanced synthetic benchmark with patterns inspired by CTU-13 and IoT-23. It does **not** currently load and evaluate the original raw CTU-13 or IoT-23 corpora. Features are split into train, validation, and test sets; the scaler is fit on the training split only. Results from this generated benchmark are for demonstration and must not be presented as real-world performance.

The training script runs each comparison architecture for at least 50 epochs and writes an independent test-metrics CSV:

| CSV file | Model |
|---|---|
| `saved_weights/standalone_cnn_metrics.csv` | Standalone CNN |
| `saved_weights/standalone_lstm_metrics.csv` | Standalone LSTM |
| `saved_weights/hybrid_cnn_lstm_metrics.csv` | Hybrid CNN-LSTM (used by the API) |

Metrics are computed from each architecture's selected best validation-F1 checkpoint on the held-out test split. Run training before quoting results; do not reuse earlier README figures as measured results.

---

## 3. Directory Layout & Artifacts

| File / Folder | Purpose |
|---|---|
| `dataset.py` | Synthetic traffic generator, train/validation/test split, feature scaling, and temporal window creation. |
| `model.py` | PyTorch architectures (`StandaloneCNN`, `StandaloneLSTM`, `HybridCNNLSTM`) & graph formatter. |
| `train.py` | Trains and evaluates all three architectures, exports per-model CSV metrics, and saves checkpoints. |
| `evaluate.py` | Standalone research evaluation and graph-payload helper; the web app uses `backend/app/services/ml_service.py` instead. |
| `saved_weights/best_hybrid_cnn_lstm.pth` | Serialized PyTorch state dict and optimizer checkpoint. |
| `saved_weights/traffic_scaler.joblib` | Fitted StandardScaler for numerical network features. |
| `saved_weights/training_metrics.json` | Epoch-wise histories and test metrics for all three traffic architectures. |
| `saved_weights/*_metrics.csv` | Separate test-metric row for each traffic model. |
| `saved_weights/training_curves.png` | Loss and Accuracy/F1 training trajectory plots. |

---

## 4. Execution Commands

```powershell
# Train all three comparison models for at least 50 epochs
& "d:\crimegraphai\.venv\Scripts\python.exe" d:\crimegraphai\models\botnet_cnn_lstm\train.py

# Run live inference and generate Cypher statements
& "d:\crimegraphai\.venv\Scripts\python.exe" d:\crimegraphai\models\botnet_cnn_lstm\evaluate.py
```
