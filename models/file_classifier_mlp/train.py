"""
Training & Explainability Pipeline for Evidence File-Type Classifier (Paper 5).
Compares Random Forest Baseline vs Proposed MLP and generates SHAP explainability insights.
"""

import os
import json
import csv
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
    output_dir: str = "saved_models",
    epochs: int = 50,
):
    if epochs < 50:
        raise ValueError("MLP training requires at least 50 epochs.")

    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Dataset Loading
    print(f"[*] Generating Govdocs1-style evidence benchmark ({num_samples} samples)...")
    df = load_govdocs_dataset(num_samples=num_samples)
    
    X = df["content"].values
    y = df["label"].values
    
    X_train_validation, X_test, y_train_validation, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    X_train, X_validation, y_train, y_validation = train_test_split(
        X_train_validation,
        y_train_validation,
        test_size=0.20,
        random_state=42,
        stratify=y_train_validation,
    )
    print(
        f"[*] Train: {len(X_train)}, validation: {len(X_validation)}, "
        f"test: {len(X_test)} samples across {len(np.unique(y))} generated categories."
    )
    
    # 2. Pipeline Training
    print("\n" + "="*55)
    print("[*] Training Baseline (Random Forest) and Proposed MLP (Paper 5)...")
    print("="*55)
    
    pipeline = EvidenceClassifierPipeline(max_features=500, epochs=epochs)
    X_train_tfidf = pipeline.vectorizer.fit_transform(X_train)
    X_validation_tfidf = pipeline.vectorizer.transform(X_validation)
    X_test_tfidf = pipeline.vectorizer.transform(X_test)

    rf_start = time.time()
    pipeline.rf_baseline.fit(X_train_tfidf, y_train)
    rf_duration = time.time() - rf_start

    mlp_start = time.time()
    classes = np.unique(y_train)
    mlp_history = {"epoch": [], "training_loss": [], "validation_accuracy": [], "validation_f1": []}
    for epoch in range(1, epochs + 1):
        pipeline.mlp_model.partial_fit(
            X_train_tfidf,
            y_train,
            classes=classes if epoch == 1 else None,
        )
        validation_predictions = pipeline.mlp_model.predict(X_validation_tfidf)
        validation_metrics = evaluate_model_performance(
            y_validation,
            validation_predictions,
            "Validation",
        )
        mlp_history["epoch"].append(epoch)
        mlp_history["training_loss"].append(float(pipeline.mlp_model.loss_))
        mlp_history["validation_accuracy"].append(validation_metrics["accuracy"])
        mlp_history["validation_f1"].append(validation_metrics["weighted_f1"])
        if epoch % 10 == 0 or epoch == epochs:
            print(
                f"[*] MLP epoch {epoch}/{epochs} | "
                f"loss={pipeline.mlp_model.loss_:.4f} | "
                f"validation F1={validation_metrics['weighted_f1']:.4f}"
            )
    mlp_duration = time.time() - mlp_start
    pipeline.is_fitted = True
    pipeline.classes_ = pipeline.mlp_model.classes_
    print(f"[+] MLP trained for exactly {epochs} epochs.")
    
    # 3. Model Evaluation & Comparison
    print("\n[*] Evaluating on Test Set...")
    rf_preds = pipeline.rf_baseline.predict(X_test_tfidf)
    mlp_preds = pipeline.mlp_model.predict(X_test_tfidf)
    
    rf_metrics = evaluate_model_performance(y_test, rf_preds, "Baseline: Random Forest")
    mlp_metrics = evaluate_model_performance(y_test, mlp_preds, "Proposed: MLP + TF-IDF (Paper 5)")
    
    print("\n" + "="*95)
    print("      MODEL 2: EVIDENCE FILE-TYPE CLASSIFIER (PAPER 5) - BENCHMARK METRICS")
    print("="*95)
    print(f"{'Model Name':<28} | {'Role':<12} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'Weighted F1':<11} | {'Macro F1':<8}")
    print("-"*95)
    print(f"{'Random Forest':<28} | {'Baseline':<12} | {rf_metrics['accuracy']*100:.2f}%{'':<3} | {rf_metrics['weighted_precision']*100:.2f}%{'':<3} | {rf_metrics['weighted_recall']*100:.2f}%{'':<3} | {rf_metrics['weighted_f1']:.4f}{'':<5} | {rf_metrics['macro_f1']:.4f}{'':<2}")
    print(f"{'MLP Classifier (Paper 5)':<28} | {'Proposed':<12} | {mlp_metrics['accuracy']*100:.2f}%{'':<3} | {mlp_metrics['weighted_precision']*100:.2f}%{'':<3} | {mlp_metrics['weighted_recall']*100:.2f}%{'':<3} | {mlp_metrics['weighted_f1']:.4f}{'':<5} | {mlp_metrics['macro_f1']:.4f}{'':<2}")
    print("="*95)

    csv_metrics = [
        {
            "model": "Random Forest",
            "role": "Baseline",
            "dataset": "generated Govdocs1-style file fragments",
            "training_epochs": "not_applicable",
            "training_method": "100 trees; max_depth=20",
            "training_time_seconds": round(rf_duration, 4),
            **{f"test_{key}": value for key, value in rf_metrics.items() if key != "model_name"},
        },
        {
            "model": "TF-IDF + MLP",
            "role": "Primary",
            "dataset": "generated Govdocs1-style file fragments",
            "training_epochs": epochs,
            "training_method": "Adam; partial_fit; batch_size=64; learning_rate=0.001",
            "training_time_seconds": round(mlp_duration, 4),
            **{f"test_{key}": value for key, value in mlp_metrics.items() if key != "model_name"},
        },
    ]
    csv_fields = [
        "model", "role", "dataset", "training_epochs", "training_method",
        "training_time_seconds", "test_accuracy", "test_weighted_precision",
        "test_weighted_recall", "test_weighted_f1", "test_macro_f1",
    ]
    for metrics in csv_metrics:
        metrics_path = os.path.join(
            output_dir,
            "random_forest_metrics.csv" if metrics["model"] == "Random Forest" else "mlp_metrics.csv",
        )
        with open(metrics_path, "w", newline="", encoding="utf-8") as metrics_file:
            writer = csv.DictWriter(metrics_file, fieldnames=csv_fields)
            writer.writeheader()
            writer.writerow(metrics)
        print(f"[+] Model metrics saved: {metrics_path}")
    
    # 4. Save Models
    pipeline.save(output_dir)
    
    # 5. SHAP Explainability Engine
    print("\n[*] Computing SHAP Explainability feature importances...")
    # Transform sample for explainability
    sample_indices = np.random.default_rng(42).choice(
        len(X_test), size=min(150, len(X_test)), replace=False
    )
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
        "dataset": "generated Govdocs1-style file-fragment benchmark",
        "training_epochs": epochs,
        "training_time_seconds": round(rf_duration + mlp_duration, 2),
        "training_times_seconds": {
            "random_forest": round(rf_duration, 4),
            "mlp": round(mlp_duration, 4),
        },
        "baseline_rf": rf_metrics,
        "proposed_mlp": mlp_metrics,
        "mlp_history": mlp_history,
        "top_diagnostic_features": feature_names[top_indices][::-1].tolist()
    }
    
    with open(os.path.join(output_dir, "model_comparison.json"), "w") as f:
        json.dump(summary_report, f, indent=2)
        
    print(f"[+] Model comparison metrics saved to: {os.path.join(output_dir, 'model_comparison.json')}")
    return summary_report

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    saved_models_dir = os.path.join(current_dir, "saved_models")
    run_training_and_explainability(num_samples=6000, output_dir=saved_models_dir, epochs=50)
