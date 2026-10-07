"""
Evidence File-Type Classifier Pipeline (Paper 5).
Combines TF-IDF n-gram vectorization with:
- Random Forest Classifier (Baseline)
- Multi-Layer Perceptron (MLPClassifier, Primary Model)
- Neo4j Graph Entity Formatter
"""

import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier

class EvidenceClassifierPipeline:
    def __init__(self, max_features: int = 600, epochs: int = 50):
        if epochs < 50:
            raise ValueError("MLP training requires at least 50 epochs.")

        self.epochs = epochs
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        # Baseline Model: Random Forest (Paper 5 baseline)
        self.rf_baseline = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        # Primary Model: Multi-Layer Perceptron (MLP)
        self.mlp_model = MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            solver="adam",
            alpha=0.0001,
            batch_size=64,
            learning_rate_init=0.001,
            max_iter=1,
            early_stopping=False,
            random_state=42
        )
        self.is_fitted = False
        self.classes_ = None

    def fit(self, texts, labels):
        X_tfidf = self.vectorizer.fit_transform(texts)
        self.rf_baseline.fit(X_tfidf, labels)
        classes = np.unique(labels)
        for epoch in range(self.epochs):
            self.mlp_model.partial_fit(
                X_tfidf,
                labels,
                classes=classes if epoch == 0 else None,
            )
        self.is_fitted = True
        self.classes_ = self.mlp_model.classes_
        return self

    def predict_mlp(self, texts):
        X_tfidf = self.vectorizer.transform(texts)
        return self.mlp_model.predict(X_tfidf)

    def predict_proba_mlp(self, texts):
        X_tfidf = self.vectorizer.transform(texts)
        return self.mlp_model.predict_proba(X_tfidf)

    def predict_baseline(self, texts):
        X_tfidf = self.vectorizer.transform(texts)
        return self.rf_baseline.predict(X_tfidf)

    def save(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        joblib.dump(self.vectorizer, os.path.join(output_dir, "tfidf_vectorizer.joblib"))
        joblib.dump(self.mlp_model, os.path.join(output_dir, "mlp_classifier.joblib"))
        joblib.dump(self.rf_baseline, os.path.join(output_dir, "rf_baseline.joblib"))
        print(f"[+] All models and vectorizer saved to: {output_dir}")

    @classmethod
    def load(cls, output_dir: str):
        instance = cls()
        instance.vectorizer = joblib.load(os.path.join(output_dir, "tfidf_vectorizer.joblib"))
        instance.mlp_model = joblib.load(os.path.join(output_dir, "mlp_classifier.joblib"))
        instance.rf_baseline = joblib.load(os.path.join(output_dir, "rf_baseline.joblib"))
        instance.is_fitted = True
        instance.classes_ = instance.mlp_model.classes_
        return instance

def format_file_evidence_graph_node(
    file_id: str,
    file_name: str,
    predicted_type: str,
    confidence: float,
    device_id: str = "DEV_SEIZED_001",
    case_id: str = "CASE_2026_09",
    top_features: list = None
) -> dict:
    """
    Creates Neo4j graph payload for forensic file evidence nodes.
    """
    return {
        "file_node": {
            "label": "EvidenceFile",
            "properties": {
                "file_id": file_id,
                "name": file_name,
                "forensic_type": predicted_type,
                "confidence": round(float(confidence), 4),
                "key_signatures": top_features or []
            }
        },
        "device_node": {
            "label": "DigitalDevice",
            "properties": {"device_id": device_id}
        },
        "case_node": {
            "label": "InvestigationCase",
            "properties": {"case_id": case_id}
        },
        "relationships": [
            {
                "type": "RECOVERED_FROM_DEVICE",
                "from": "EvidenceFile",
                "to": "DigitalDevice"
            },
            {
                "type": "ASSOCIATED_WITH_CASE",
                "from": "EvidenceFile",
                "to": "InvestigationCase"
            }
        ]
    }
