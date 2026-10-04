"""
CrimeGraph AI - Master Training Pipeline Orchestrator.
Trains and verifies both Paper 8 (CNN-LSTM) and Paper 5 (Govdocs1 MLP + SHAP) models.
"""

import sys
import os
import time
import json

# Add model directories to system path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
botnet_dir = os.path.join(base_dir, "models", "botnet_cnn_lstm")
file_clf_dir = os.path.join(base_dir, "models", "file_classifier_mlp")
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from models.botnet_cnn_lstm.train import run_training as train_botnet_model
from models.file_classifier_mlp.train import run_training_and_explainability as train_file_model

def run_all_training():
    print("=" * 70)
    print("   CRIMEGRAPH AI - DUAL MODEL TRAINING & BENCHMARKING PIPELINE")
    print("=" * 70)
    
    total_start = time.time()
    
    # -------------------------------------------------------------
    # 1. Model 1: Botnet Detection (Paper 8: CNN + LSTM Hybrid)
    # -------------------------------------------------------------
    print("\n>>> STEP 1/2: Training Model 1 - Botnet Detector (CTU-13 / IoT-23)")
    botnet_weights_dir = os.path.join(botnet_dir, "saved_weights")
    botnet_summary = train_botnet_model(
        epochs=12,
        batch_size=64,
        seq_len=8,
        num_samples=10000,
        output_dir=botnet_weights_dir
    )
    
    # -------------------------------------------------------------
    # 2. Model 2: Forensic File Classifier (Paper 5: MLP + SHAP)
    # -------------------------------------------------------------
    print("\n>>> STEP 2/2: Training Model 2 - File Evidence Classifier (Govdocs1)")
    file_models_dir = os.path.join(file_clf_dir, "saved_models")
    file_summary = train_file_model(
        num_samples=6000,
        output_dir=file_models_dir
    )
    
    total_duration = time.time() - total_start
    
    # Consolidated Report
    master_report = {
        "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_runtime_seconds": round(total_duration, 2),
        "model_1_botnet_traffic_detector": {
            "source_paper": "Paper 8",
            "dataset": "CTU-13 / IoT-23",
            "architecture": "Hybrid CNN-LSTM (1D Conv + Bidirectional LSTM)",
            "test_accuracy": botnet_summary["test_metrics"]["accuracy"],
            "test_precision": botnet_summary["test_metrics"]["precision"],
            "test_recall": botnet_summary["test_metrics"]["recall"],
            "test_f1_score": botnet_summary["test_metrics"]["f1"],
            "test_roc_auc": botnet_summary["test_metrics"]["auc"],
            "weights_path": os.path.join(botnet_weights_dir, "best_hybrid_cnn_lstm.pth")
        },
        "model_2_evidence_file_classifier": {
            "source_paper": "Paper 5",
            "dataset": "Govdocs1",
            "baseline_model": "Random Forest",
            "proposed_model": "MLP Classifier with TF-IDF",
            "explainability": "SHAP (TreeExplainer / Shapley values)",
            "baseline_accuracy": file_summary["baseline_rf"]["accuracy"],
            "baseline_f1": file_summary["baseline_rf"]["weighted_f1"],
            "proposed_mlp_accuracy": file_summary["proposed_mlp"]["accuracy"],
            "proposed_mlp_f1": file_summary["proposed_mlp"]["weighted_f1"],
            "models_path": file_models_dir
        }
    }
    
    report_path = os.path.join(base_dir, "data", "processed", "training_summary_report.json")
    with open(report_path, "w") as f:
        json.dump(master_report, f, indent=2)
        
    print("\n" + "=" * 70)
    print("   ALL 2 MODELS SUCCESSFULLY TRAINED AND VERIFIED!")
    print(f"   Total Pipeline Runtime: {total_duration:.2f} seconds")
    print(f"   Full Report Saved: {report_path}")
    print("=" * 70)
    
    return master_report

if __name__ == "__main__":
    run_all_training()
