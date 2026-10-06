# ==============================================================================
# CrimeGraph AI - Application Configuration & Environment Variables
# ==============================================================================
# This module loads settings from .env file or environment variables.
# Used across FastAPI routes, local graph storage, and LLM services.

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "CrimeGraph AI"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # LLM Provider Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    # Local Machine Learning Weights Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    DATABASE_PATH: str = os.getenv("CRIMEGRAPH_DATABASE_PATH", os.path.join(BASE_DIR, "data", "crimegraph.sqlite3"))
    BOTNET_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "botnet_cnn_lstm", "saved_weights", "best_hybrid_cnn_lstm.pth")
    BOTNET_SCALER_PATH: str = os.path.join(BASE_DIR, "models", "botnet_cnn_lstm", "saved_weights", "traffic_scaler.joblib")
    FILE_MLP_PATH: str = os.path.join(BASE_DIR, "models", "file_classifier_mlp", "saved_models", "mlp_classifier.joblib")
    FILE_TFIDF_PATH: str = os.path.join(BASE_DIR, "models", "file_classifier_mlp", "saved_models", "tfidf_vectorizer.joblib")

    class Config:
        case_sensitive = True

settings = Settings()
