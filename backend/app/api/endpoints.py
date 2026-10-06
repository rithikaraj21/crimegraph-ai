# ==============================================================================
# CrimeGraph AI - REST API Route Controllers
# ==============================================================================
# Defines clean, documented endpoints for:
# 1. Healthcheck & model readiness
# 2. Case Graph Retrieval (Cytoscape.js format)
# 3. LLM FIR & Narrative Entity Extraction
# 4. Model 1: Botnet CNN-LSTM Traffic Inference
# 5. Model 2: Evidence File Classifier & Explainability

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.core.config import settings
from app.schemas.graph import (
    GraphResponse,
    CaseNarrativeInput,
    NetworkTrafficInput,
    FileEvidenceInput,
    CreateCaseInput,
)
from app.services.llm_service import LLMExtractorService
from app.services.ml_service import MLInferenceService
from app.services.graph_service import GraphService

router = APIRouter()

@router.get("/health", tags=["System"])
def system_health() -> Dict[str, Any]:
    """Returns system status, active database drivers, and model weights readiness."""
    models = MLInferenceService.readiness()
    return {
        "status": "ONLINE",
        "database_mode": "SQLite (persistent local storage)",
        "models_ready": {
            **models,
            "narrative_extractor": True,
        },
        "narrative_extractor_mode": "Gemini with local fallback" if settings.GEMINI_API_KEY else "Local pattern extractor",
    }

@router.get("/cases", tags=["Cases"])
def list_cases():
    return {"cases": GraphService.list_cases()}

@router.post("/cases", status_code=status.HTTP_201_CREATED, tags=["Cases"])
def create_case(payload: CreateCaseInput):
    try:
        return GraphService.create_case(payload.case_id, payload.title, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

@router.get("/cases/{case_id}/graph", response_model=GraphResponse, tags=["Forensic Graph"])
def get_investigation_graph(case_id: str):
    """
    Fetches the complete POLE knowledge graph for the specified case.
    Compatible directly with Cytoscape.js canvas renderers.
    """
    try:
        return GraphService.get_case_graph(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

@router.post("/cases/extract-narrative", tags=["LLM Intelligence"])
def extract_case_narrative(payload: CaseNarrativeInput) -> Dict[str, Any]:
    """
    Processes an unstructured police FIR narrative using the LLM extraction pipeline.
    Identifies Suspects, Phone numbers, Locations, and links them into the graph.
    """
    try:
        extracted = LLMExtractorService.extract_from_narrative(payload.narrative_text, payload.case_id)
        updated_graph = GraphService.add_extracted_entities(payload.case_id, extracted)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "case_id": payload.case_id,
        "message": f"Successfully extracted {len(extracted['nodes'])} POLE entities and {len(extracted['relationships'])} links.",
        "extractor": extracted["extractor"],
        "extracted_entities": extracted,
        "total_graph_nodes": len(updated_graph["nodes"]),
        "total_graph_edges": len(updated_graph["edges"])
    }

@router.post("/models/botnet/predict", tags=["Machine Learning Models"])
def predict_network_traffic(flow: NetworkTrafficInput) -> Dict[str, Any]:
    """
    Evaluates a suspicious NetFlow record with the trained PyTorch Hybrid CNN-LSTM model.
    Flags botnet C&C beaconing or DDoS floods and creates an IP node edge.
    """
    try:
        result = MLInferenceService.predict_traffic_flow(flow)
        graph = GraphService.add_traffic_result(flow.case_id, result)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    result["total_graph_nodes"] = len(graph["nodes"])
    result["total_graph_edges"] = len(graph["edges"])
    return result

@router.post("/models/file-classifier/predict", tags=["Machine Learning Models"])
def classify_file_evidence(evidence: FileEvidenceInput) -> Dict[str, Any]:
    """
    Classifies a hexadecimal byte sample with the trained MLP and reports
    recognized file-header signatures as diagnostic context.
    """
    try:
        result = MLInferenceService.classify_file_evidence(evidence)
        graph = GraphService.add_file_result(evidence.case_id, result)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    result["total_graph_nodes"] = len(graph["nodes"])
    result["total_graph_edges"] = len(graph["edges"])
    return result
