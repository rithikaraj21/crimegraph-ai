"""
Forensic File Explainability & Neo4j Ingestion Engine (Paper 5).
Explains why an evidence file was classified as a specific format
and produces Cypher queries for the CrimeGraph AI graph database.
"""

import os
import json
import numpy as np
from model import EvidenceClassifierPipeline, format_file_evidence_graph_node

def analyze_and_explain_evidence_file(
    file_id: str,
    file_name: str,
    file_content_hex: str,
    models_dir: str,
    case_id: str = "CASE_2026_09",
    device_id: str = "SEIZED_LAPTOP_04"
) -> dict:
    pipeline = EvidenceClassifierPipeline.load(models_dir)
    
    # Predict probabilities
    probs = pipeline.predict_proba_mlp([file_content_hex])[0]
    predicted_idx = np.argmax(probs)
    predicted_class = pipeline.classes_[predicted_idx]
    confidence = probs[predicted_idx]
    
    # Extract top matching tokens present in this fragment
    vectorizer = pipeline.vectorizer
    transformed = vectorizer.transform([file_content_hex])
    feature_names = np.array(vectorizer.get_feature_names_out())
    
    nonzero_indices = transformed.nonzero()[1]
    scores = transformed.data
    
    sorted_order = np.argsort(scores)[::-1]
    top_tokens = [feature_names[nonzero_indices[i]] for i in sorted_order[:5]] if len(nonzero_indices) > 0 else []
    
    graph_payload = format_file_evidence_graph_node(
        file_id=file_id,
        file_name=file_name,
        predicted_type=predicted_class,
        confidence=confidence,
        device_id=device_id,
        case_id=case_id,
        top_features=top_tokens
    )
    
    # Neo4j Cypher Injection Statement
    cypher = f"""
    MERGE (case:InvestigationCase {{case_id: '{case_id}'}})
    MERGE (dev:DigitalDevice {{device_id: '{device_id}'}})
    MERGE (f:EvidenceFile {{file_id: '{file_id}'}})
    ON CREATE SET 
        f.name = '{file_name}',
        f.detected_type = '{predicted_class}',
        f.confidence = {round(confidence, 4)},
        f.key_signatures = {json.dumps(top_tokens)},
        f.ingestion_time = timestamp()
    MERGE (f)-[:RECOVERED_FROM]->(dev)
    MERGE (dev)-[:EVIDENCE_IN]->(case)
    RETURN f, dev, case;
    """
    
    return {
        "file_id": file_id,
        "file_name": file_name,
        "predicted_type": predicted_class,
        "confidence": round(float(confidence), 4),
        "explainable_signatures": top_tokens,
        "graph_node_payload": graph_payload,
        "cypher_query": cypher.strip()
    }

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    saved_models_dir = os.path.join(current_dir, "saved_models")
    
    # Sample carved PDF header fragment
    sample_hex = "25 50 44 46 2d 2f 54 79 70 65 2f 43 61 74 61 6c 6f 67 6f 62 6a 65 6e 64 6f 62 6a 73 74 72 65 61 6d"
    
    print("[*] Running explainable forensic analysis on recovered file fragment...")
    result = analyze_and_explain_evidence_file(
        file_id="EVID_FILE_0821",
        file_name="financial_ledger_fragment.raw",
        file_content_hex=sample_hex,
        models_dir=saved_models_dir
    )
    print(json.dumps(result, indent=2))
