"""
Training pipeline for Botnet & Malicious Traffic Detection (Paper 8).
Trains the Primary Hybrid CNN-LSTM architecture and generates comparative metrics.
"""

import os
import json
import csv
import time
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

try:
    from .dataset import generate_benchmark_traffic, prepare_dataloaders
    from .model import HybridCNNLSTM, StandaloneCNN, StandaloneLSTM
except (ImportError, ValueError):
    from dataset import generate_benchmark_traffic, prepare_dataloaders
    from model import HybridCNNLSTM, StandaloneCNN, StandaloneLSTM

def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    all_preds, all_labels = [], []
    
    for batch_x, batch_y in loader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)
        optimizer.zero_grad()
        logits = model(batch_x)
        loss = criterion(logits, batch_y)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item() * len(batch_y)
        probs = torch.sigmoid(logits).detach().cpu().numpy()
        all_preds.extend((probs >= 0.5).astype(int))
        all_labels.extend(batch_y.detach().cpu().numpy())
        
    avg_loss = total_loss / len(loader.dataset)
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, zero_division=0)
    return avg_loss, acc, f1

def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_probs, all_preds, all_labels = [], [], []
    
    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            
            total_loss += loss.item() * len(batch_y)
            probs = torch.sigmoid(logits).cpu().numpy()
            all_probs.extend(probs)
            all_preds.extend((probs >= 0.5).astype(int))
            all_labels.extend(batch_y.cpu().numpy())
            
    avg_loss = total_loss / len(loader.dataset)
    acc = accuracy_score(all_labels, all_preds)
    prec = precision_score(all_labels, all_preds, zero_division=0)
    rec = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)
    try:
        auc = roc_auc_score(all_labels, all_probs)
    except Exception:
        auc = 0.5
        
    return {
        "loss": avg_loss,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "auc": auc
    }

def run_training(
    epochs: int = 50,
    batch_size: int = 64, 
    seq_len: int = 8, 
    lr: float = 0.001,
    num_samples: int = 10000,
    output_dir: str = "saved_weights"
):
    if epochs < 50:
        raise ValueError("Traffic model training requires at least 50 epochs.")

    np.random.seed(42)
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Training on device: {device}")
    
    # 1. Dataset Generation & Loading
    print(f"[*] Generating benchmark CTU-13 / IoT-23 traffic flows ({num_samples} flows)...")
    df = generate_benchmark_traffic(num_samples=num_samples, random_seed=42)
    scaler_path = os.path.join(output_dir, "traffic_scaler.joblib")
    
    train_loader, val_loader, test_loader, scaler = prepare_dataloaders(
        df, seq_len=seq_len, batch_size=batch_size, scaler_save_path=scaler_path
    )
    print(f"[*] Sequences generated - Train: {len(train_loader.dataset)}, Val: {len(val_loader.dataset)}, Test: {len(test_loader.dataset)}")
    
    # Train every traffic architecture on the same generated split. The historical
    # baseline figures were not produced by this training script and are not reused.
    architectures = [
        ("standalone_cnn", "Standalone CNN", StandaloneCNN(num_features=15)),
        ("standalone_lstm", "Standalone LSTM", StandaloneLSTM(num_features=15)),
        ("hybrid_cnn_lstm", "Hybrid CNN-LSTM", HybridCNNLSTM(num_features=15, cnn_filters=64, lstm_hidden=64)),
    ]
    model_results = {}
    csv_fields = [
        "model", "dataset", "epochs_trained", "training_time_seconds",
        "test_loss", "test_accuracy", "test_precision", "test_recall", "test_f1", "test_auc",
    ]

    for model_key, model_name, model in architectures:
        print("\n" + "=" * 60)
        print(f"[*] Training {model_name}: {epochs} epochs")
        print("=" * 60)
        model = model.to(device)
        criterion = nn.BCEWithLogitsLoss()
        optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=2
        )
        history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": [], "val_f1": []}
        best_f1 = -1.0
        best_weights_path = os.path.join(output_dir, f"best_{model_key}.pth")
        start_time = time.time()

        for epoch in range(1, epochs + 1):
            train_loss, train_acc, _ = train_one_epoch(
                model, train_loader, criterion, optimizer, device
            )
            val_metrics = evaluate(model, val_loader, criterion, device)
            scheduler.step(val_metrics["loss"])
            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_metrics["loss"])
            history["train_acc"].append(train_acc)
            history["val_acc"].append(val_metrics["accuracy"])
            history["val_f1"].append(val_metrics["f1"])

            if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
                print(
                    f"{model_name} | Epoch {epoch:02d}/{epochs:02d} | "
                    f"Train loss {train_loss:.4f} | Val loss {val_metrics['loss']:.4f} | "
                    f"Val F1 {val_metrics['f1']:.4f}"
                )
            if val_metrics["f1"] > best_f1:
                best_f1 = val_metrics["f1"]
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "f1_score": best_f1,
                    "val_metrics": val_metrics,
                }, best_weights_path)

        training_duration = time.time() - start_time
        checkpoint = torch.load(best_weights_path, map_location=device, weights_only=True)
        model.load_state_dict(checkpoint["model_state_dict"])
        test_metrics = evaluate(model, test_loader, criterion, device)
        result = {
            "model": model_name,
            "dataset": "generated CTU-13/IoT-23-style benchmark traffic",
            "epochs_trained": epochs,
            "training_time_seconds": round(training_duration, 2),
            "test_metrics": test_metrics,
            "history": history,
        }
        model_results[model_key] = result
        csv_row = {
            "model": model_name,
            "dataset": result["dataset"],
            "epochs_trained": epochs,
            "training_time_seconds": round(training_duration, 2),
            **{f"test_{key}": value for key, value in test_metrics.items()},
        }
        metrics_path = os.path.join(output_dir, f"{model_key}_metrics.csv")
        with open(metrics_path, "w", newline="", encoding="utf-8") as metrics_file:
            writer = csv.DictWriter(metrics_file, fieldnames=csv_fields)
            writer.writeheader()
            writer.writerow(csv_row)
        print(f"[+] Test metrics saved: {metrics_path}")

    # Keep the deployed artifact filename stable for the inference service.
    hybrid = model_results["hybrid_cnn_lstm"]
    hybrid_checkpoint = torch.load(
        os.path.join(output_dir, "best_hybrid_cnn_lstm.pth"),
        map_location=device,
        weights_only=True,
    )
    torch.save(hybrid_checkpoint, os.path.join(output_dir, "best_hybrid_cnn_lstm.pth"))

    metrics_summary = {
        "dataset": "generated CTU-13/IoT-23-style benchmark traffic",
        "models": model_results,
    }
    with open(os.path.join(output_dir, "training_metrics.json"), "w") as f:
        json.dump(metrics_summary, f, indent=2)

    history = hybrid["history"]
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history["train_loss"], label="Train Loss", color="royalblue")
    plt.plot(history["val_loss"], label="Val Loss", color="orange")
    plt.title("Cross-Entropy Loss Curve")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(history["train_acc"], label="Train Acc", color="royalblue")
    plt.plot(history["val_acc"], label="Val Acc", color="orange")
    plt.plot(history["val_f1"], label="Val F1", color="green", linestyle="--")
    plt.title("Accuracy & F1 Score")
    plt.xlabel("Epoch")
    plt.ylabel("Score")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    chart_path = os.path.join(output_dir, "training_curves.png")
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"[+] Training curves saved to: {chart_path}")

    print("\nTest-set results on generated benchmark data")
    for result in model_results.values():
        metrics = result["test_metrics"]
        print(
            f"{result['model']}: accuracy={metrics['accuracy']:.4f}, "
            f"precision={metrics['precision']:.4f}, recall={metrics['recall']:.4f}, "
            f"F1={metrics['f1']:.4f}, ROC-AUC={metrics['auc']:.4f}"
        )

    return metrics_summary

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    saved_weights_dir = os.path.join(current_dir, "saved_weights")
    run_training(epochs=50, batch_size=64, output_dir=saved_weights_dir)
