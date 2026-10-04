"""
Inference & Graph Extraction Engine for Botnet Traffic (Paper 8).
Loads trained Hybrid CNN-LSTM weights, predicts flow threats,
and generates Cypher queries for Neo4j graph population.
"""

import os
import json
import torch
import joblib
import numpy as np
import pandas as pd
from model import HybridCNNLSTM, format_graph_edge
from dataset import FEATURE_COLUMNS

def load_inference_pipeline(weights_dir: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    weights_path = os.path.join(weights_dir, "best_hybrid_cnn_lstm.pth")
    scaler_path = os.path.join(weights_dir, "traffic_scaler.joblib")
    
    if not os.path.exists(weights_path) or not os.path.exists(scaler_path):
        raise FileNotFoundError("Model weights or scaler not found. Run train.py first.")
        
    scaler = joblib.load(scaler_path)
    model = HybridCNNLSTM(num_features=len(FEATURE_COLUMNS), cnn_filters=64, lstm_hidden=64).to(device)
    checkpoint = torch.load(weights_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    
    return model, scaler, device

def analyze_traffic_for_graph(flow_records: list, weights_dir: str, seq_len: int = 8):
    """
    Takes a list of flow dictionaries, runs CNN-LSTM prediction, and generates
    Neo4j Cypher statements to inject malicious IP nodes and edges into the graph.
    """
    model, scaler, device = load_inference_pipeline(weights_dir)
    
    results = []
    cypher_queries = []
    
    # Process sequence
    df_flows = pd.DataFrame(flow_records)
    X = df_flows[FEATURE_COLUMNS].values
    X_scaled = scaler.transform(X)
    
    # Pad if fewer than seq_len
    if len(X_scaled) < seq_len:
        pad_size = seq_len - len(X_scaled)
        X_scaled = np.pad(X_scaled, ((0, pad_size), (0, 0)), mode="edge")
        
    # Take window
    x_tensor = torch.tensor(X_scaled[:seq_len], dtype=torch.float32).unsqueeze(0).to(device)
    
    with torch.no_grad():
        logits = model(x_tensor)
        prob = torch.sigmoid(logits).item()
        is_malicious = prob >= 0.5
        
    src_ip = flow_records[0].get("src_ip", "192.168.1.105")
    dst_ip = flow_records[0].get("dst_ip", "185.220.101.5")
    protocol = flow_records[0].get("protocol", "TCP")
    attack_type = "C&C_Beaconing" if is_malicious else "Normal_Flow"
    
    graph_edge = format_graph_edge(
        src_ip=src_ip,
        dst_ip=dst_ip,
        is_malicious=is_malicious,
        confidence_score=prob if is_malicious else (1.0 - prob),
        protocol=protocol,
        attack_category=attack_type
    )
    
    # Generate Cypher Query for Neo4j
    if is_malicious:
        cypher = f"""
        MERGE (src:IPAddress {{ip: '{src_ip}'}})
        ON CREATE SET src.status = 'Compromised_Bot', src.first_seen = timestamp()
        MERGE (c2:IPAddress {{ip: '{dst_ip}'}})
        ON CREATE SET c2.status = 'C2_Server', c2.first_seen = timestamp()
        MERGE (src)-[r:MALICIOUS_BOTNET_COMMUNICATION {{
            confidence: {round(prob, 4)},
            attack_type: '{attack_type}',
            protocol: '{protocol}'
        }}]->(c2)
        RETURN src, r, c2;
        """
    else:
        cypher = f"""
        MERGE (src:IPAddress {{ip: '{src_ip}'}})
        MERGE (dst:IPAddress {{ip: '{dst_ip}'}})
        MERGE (src)-[r:NETWORK_COMMUNICATION {{protocol: '{protocol}', is_malicious: false}}]->(dst)
        RETURN src, r, dst;
        """
        
    return {
        "is_malicious": is_malicious,
        "threat_probability": round(prob, 4),
        "classification": attack_type,
        "graph_edge": graph_edge,
        "cypher_query": cypher.strip()
    }

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    saved_weights_dir = os.path.join(current_dir, "saved_weights")
    
    # Sample suspicious beaconing flow
    sample_flows = [
        {
            "src_ip": "192.168.4.52",
            "dst_ip": "142.250.190.46",
            "protocol": "TCP",
            "duration": 0.05,
            "src_bytes": 64,
            "dst_bytes": 64,
            "src_pkts": 1,
            "dst_pkts": 1,
            "flow_rate_bytes_sec": 1280.0,
            "flow_rate_pkts_sec": 20.0,
            "is_tcp": 1,
            "is_udp": 0,
            "is_icmp": 0,
            "is_common_port": 0,
            "inter_arrival_time": 5.0,
            "syn_count": 1,
            "fin_count": 0,
            "rst_count": 0
        }
    ] * 8
    
    print("[*] Running inference on sample network traffic flow...")
    analysis = analyze_traffic_for_graph(sample_flows, saved_weights_dir)
    print(json.dumps(analysis, indent=2))
