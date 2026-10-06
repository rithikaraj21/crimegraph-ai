# ==============================================================================
# CrimeGraph AI - FastAPI Application Entrypoint
# ==============================================================================
# Starts the ASGI application, configures CORS middleware for React UI,
# and mounts all forensic investigation endpoints.

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.graph_service import GraphService
from app.services.ml_service import MLInferenceService
from app.api.endpoints import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="AI-Assisted Digital Investigation & Crime Knowledge Graph System",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for React + Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip().rstrip("/")
        for origin in settings.ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application Startup Event
@app.on_event("startup")
def startup_event():
    logger.info("=" * 60)
    logger.info("   STARTING CRIMEGRAPH AI BACKEND SERVICES")
    logger.info("=" * 60)

    # 1. Initialize the local case database
    GraphService.initialize()

    # 2. Pre-load Machine Learning weights
    try:
        MLInferenceService.load_models()
        logger.info("[+] ML Models loaded into memory successfully.")
    except Exception as e:
        logger.warning(f"[-] Could not preload model weights: {e}")

# Application Shutdown Event
@app.on_event("shutdown")
def shutdown_event():
    logger.info("[*] Shutting down CrimeGraph AI services...")

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "system": "CrimeGraph AI Backend",
        "documentation": "/docs",
        "api_endpoints": f"{settings.API_V1_STR}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
