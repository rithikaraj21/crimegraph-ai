"""
Training & Explainability Pipeline for Evidence File-Type Classifier (Paper 5).
Compares Random Forest Baseline vs Proposed MLP and generates SHAP explainability insights.
"""

import os
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support
import shap

try:
    from .dataset import load_govdocs_dataset
    from .model import EvidenceClassifierPipeline
except (ImportError, ValueError):
    from dataset import load_govdocs_dataset
    from model import EvidenceClassifierPipeline

def evaluate_model_performance(y_true, y_pred, model_name: str):
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    macro_prec, macro_rec, macro_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    
    return {
        "model_name": model_name,
        "accuracy": round(float(acc), 4),
        "weighted_precision": round(float(prec), 4),
        "weighted_recall": round(float(rec), 4),
        "weighted_f1": round(float(f1), 4),
        "macro_f1": round(float(macro_f1), 4)
    }

def run_training_and_explainability(
    num_samples: int = 6000,
    output_dir: str = "saved_models"
):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Dataset Loading
    print(f"[*] Loading and preparing Govdocs1 evidence dataset ({num_samples} samples)...")
    df = load_govdocs_dataset(num_samples=num_samples)
    
    X = df["content"].values
    y = df["label"].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"[*] Train set: {len(X_train)} samples, Test set: {len(X_test)} samples across {len(np.unique(y))} categories.")
    
    # 2. Pipeline Training
    print("\n" + "="*55)
    print("[*] Training Baseline (Random Forest) and Proposed MLP (Paper 5)...")
    print("="*55)
    
    pipeline = EvidenceClassifierPipeline(max_features=500)
    start_time = time.time()
    pipeline.fit(X_train, y_train)
    fit_duration = time.time() - start_time
    print(f"[+] Fitting completed in {fit_duration:.2f} seconds.")
    
    # 3. Model Evaluation & Comparison
    print("\n[*] Evaluating on Test Set...")
    rf_preds = pipeline.predict_baseline(X_test)
    mlp_preds = pipeline.predict_mlp(X_test)
    
    rf_metrics = evaluate_model_performance(y_test, rf_preds, "Baseline: Random Forest")
    mlp_metrics = evaluate_model_performance(y_test, mlp_preds, "Proposed: MLP + TF-IDF (Paper 5)")
    
    print("\n" + "-"*55)
    print("                 MODEL COMPARISON MATRIX")
    print("-"*55)
    print(f"{'Metric':<20} | {'Random Forest (Baseline)':<24} | {'MLP Classifier':<15}")
    print("-"*55)
    for metric in ["accuracy", "weighted_precision", "weighted_recall", "weighted_f1", "macro_f1"]:
        print(f"{metric:<20} | {rf_metrics[metric]:<24} | {mlp_metrics[metric]:<15}")
    print("-"*55)
    
    # 4. Save Models
    pipeline.save(output_dir)
    
    # 5. SHAP Explainability Engine
    print("\n[*] Computing SHAP Explainability feature importances...")
    # Transform sample for explainability
    sample_indices = np.random.choice(len(X_test), size=min(150, len(X_test)), replace=False)
    X_sample_tfidf = pipeline.vectorizer.transform(X_test[sample_indices])
    
    # Use TreeExplainer on Random Forest baseline for exact Shapley values
    feature_names = np.array(pipeline.vectorizer.get_feature_names_out())
    explainer = shap.TreeExplainer(pipeline.rf_baseline)
    shap_values = explainer.shap_values(X_sample_tfidf.toarray())
    
    # Check shape of shap_values and plot global summary
    plt.figure(figsize=(9, 5))
    if isinstance(shap_values, list):
        # Multi-class: average absolute SHAP values across classes
        mean_shap = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
    elif len(shap_values.shape) == 3:
        mean_shap = np.abs(shap_values).mean(axis=(0, 2))
    else:
        mean_shap = np.abs(shap_values).mean(axis=0)
        
    top_k = 15
    top_indices = np.argsort(mean_shap)[-top_k:]
    plt.barh(range(top_k), mean_shap[top_indices], color="#2b5c8f", align="center")
    plt.yticks(range(top_k), feature_names[top_indices], fontsize=9)
    plt.xlabel("Mean |SHAP Value| (Impact on Model Classification)")
    plt.title("Top 15 Forensic Hex Signatures Driving Evidence File Classification")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    
    shap_chart_path = os.path.join(output_dir, "shap_summary.png")
    plt.savefig(shap_chart_path, dpi=150)
    plt.close()
    print(f"[+] SHAP feature importance plot saved to: {shap_chart_path}")
    
    # 6. Save Comparison JSON
    summary_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": "Govdocs1 (Digital Forensics Evidence)",
        "training_time_seconds": round(fit_duration, 2),
        "baseline_rf": rf_metrics,
        "proposed_mlp": mlp_metrics,
        "top_diagnostic_features": feature_names[top_indices][::-1].tolist()
    }
    
    with open(os.path.join(output_dir, "model_comparison.json"), "w") as f:
        json.dump(summary_report, f, indent=2)
        
    print(f"[+] Model comparison metrics saved to: {os.path.join(output_dir, 'model_comparison.json')}")
    return summary_report

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    saved_models_dir = os.path.join(current_dir, "saved_models")
    run_training_and_explainability(num_samples=6000, output_dir=saved_models_dir)
