# ==============================================================================
# CrimeGraph AI - Machine Learning Inference Service (Models 1 & 2)
# ==============================================================================
# Loads trained PyTorch Hybrid CNN-LSTM (Paper 8) and Scikit-Learn MLP (Paper 5)
# to evaluate real-time evidence payloads and generate graph updates.

import os
import joblib
import numpy as np
import torch
from typing import Dict, Any

from app.core.config import settings
from app.schemas.graph import NetworkTrafficInput, FileEvidenceInput

# Load model architectures
import sys
sys.path.insert(0, settings.BASE_DIR)
from models.botnet_cnn_lstm.model import HybridCNNLSTM

class MLInferenceService:
    _botnet_model = None
    _traffic_scaler = None
    _file_mlp = None
    _file_vectorizer = None

    @classmethod
    def load_models(cls):
        """Loads serialized model weights and preprocessors into memory once at startup."""
        # 1. Load Botnet CNN-LSTM
        if os.path.exists(settings.BOTNET_MODEL_PATH) and os.path.exists(settings.BOTNET_SCALER_PATH):
            cls._botnet_model = HybridCNNLSTM(num_features=15, cnn_filters=64, lstm_hidden=64)
            ckpt = torch.load(
                settings.BOTNET_MODEL_PATH,
                map_location=torch.device('cpu'),
                weights_only=True,
            )
            cls._botnet_model.load_state_dict(ckpt["model_state_dict"])
            cls._botnet_model.eval()
            cls._traffic_scaler = joblib.load(settings.BOTNET_SCALER_PATH)

        # 2. Load File Classifier MLP + TF-IDF
        if os.path.exists(settings.FILE_MLP_PATH) and os.path.exists(settings.FILE_TFIDF_PATH):
            cls._file_mlp = joblib.load(settings.FILE_MLP_PATH)
            cls._file_vectorizer = joblib.load(settings.FILE_TFIDF_PATH)

    @classmethod
    def readiness(cls) -> Dict[str, bool]:
        return {
            "botnet_cnn_lstm": cls._botnet_model is not None and cls._traffic_scaler is not None,
            "file_classifier_mlp": cls._file_mlp is not None and cls._file_vectorizer is not None,
        }

    @classmethod
    def predict_traffic_flow(cls, flow: NetworkTrafficInput) -> Dict[str, Any]:
        """
        Evaluates a NetFlow record with the trained Hybrid CNN-LSTM model.
        Returns the predicted class, threat probability, and model confidence.
        """
        # Ensure models are loaded
        if cls._botnet_model is None or cls._traffic_scaler is None:
            cls.load_models()
        if cls._botnet_model is None or cls._traffic_scaler is None:
            raise RuntimeError("Botnet model weights or traffic scaler are unavailable.")

        flow_rate_bytes = (flow.src_bytes + flow.dst_bytes) / max(flow.duration, 0.001)
        flow_rate_pkts = (flow.src_pkts + flow.dst_pkts) / max(flow.duration, 0.001)

        raw_features = np.array([
            flow.duration, flow.src_bytes, flow.dst_bytes, flow.src_pkts, flow.dst_pkts,
            flow_rate_bytes, flow_rate_pkts, flow.is_tcp, flow.is_udp, flow.is_icmp,
            flow.is_common_port, flow.inter_arrival_time, flow.syn_count, flow.fin_count, flow.rst_count
        ], dtype=np.float32).reshape(1, -1)

        scaled = cls._traffic_scaler.transform(raw_features)  # (1, 15)
        # Repeat single flow across seq_len=8 time steps -> (1, 8, 15)
        seq_tensor = torch.tensor(
            np.repeat(scaled[:, np.newaxis, :], 8, axis=1), dtype=torch.float32
        )

        with torch.no_grad():
            logit = cls._botnet_model(seq_tensor)
            prob = torch.sigmoid(logit).item()

        is_malicious = prob >= 0.5
        label = "MALICIOUS_BOTNET" if is_malicious else "BENIGN_TRAFFIC"
        confidence = prob if is_malicious else (1.0 - prob)

        return {
            "src_ip": flow.src_ip,
            "dst_ip": flow.dst_ip,
            "classification": label,
            "threat_score": round(prob, 4),
            "confidence": round(confidence, 4),
            "is_threat": is_malicious,
            "duration": flow.duration,
            "total_bytes": flow.src_bytes + flow.dst_bytes,
            "model": "Hybrid CNN-LSTM",
        }

    @classmethod
    def classify_file_evidence(cls, evidence: FileEvidenceInput) -> Dict[str, Any]:
        """
        Classifies carved byte fragments using the trained MLP model.
        Returns predicted category and explainable diagnostic signatures.
        """
        if cls._file_mlp is None or cls._file_vectorizer is None:
            cls.load_models()
        if cls._file_mlp is None or cls._file_vectorizer is None:
            raise RuntimeError("File classifier weights or TF-IDF vectorizer are unavailable.")

        vec = cls._file_vectorizer.transform([evidence.hex_content])
        pred_label = cls._file_mlp.predict(vec)[0]
        probs = cls._file_mlp.predict_proba(vec)[0]
        confidence = float(np.max(probs))

        # Check for recognizable magic bytes for explainability
        file_header = bytes.fromhex(evidence.hex_content)[:8]
        signatures = (
            (b"%PDF-", "%PDF header"),
            (b"MZ", "PE executable (MZ) header"),
            (b"\xff\xd8\xff", "JPEG start-of-image marker"),
            (b"PK\x03\x04", "ZIP/DOCX local file header"),
            (b"\x89PNG\r\n\x1a\n", "PNG file signature"),
            (b"GIF87a", "GIF87a file signature"),
            (b"GIF89a", "GIF89a file signature"),
        )
        diagnostic_markers = [
            description for signature, description in signatures
            if file_header.startswith(signature)
        ]
        if not diagnostic_markers:
            diagnostic_markers.append("No recognized file header; model prediction is based on byte n-grams.")

        return {
            "file_name": evidence.file_name,
            "predicted_file_type": str(pred_label),
            "confidence": round(confidence, 4),
            "diagnostic_signatures": diagnostic_markers,
            "model": "TF-IDF + MLP",
        }
