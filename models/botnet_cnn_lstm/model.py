"""
PyTorch Neural Architectures for Botnet & Malicious Traffic Detection (Paper 8).
Includes:
- StandaloneCNN (Baseline 1)
- StandaloneLSTM (Baseline 2)
- HybridCNNLSTM (Paper 8 Primary Architecture: Conv1D spatial + LSTM temporal)
- Graph Node Formatter for Neo4j integration
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class StandaloneCNN(nn.Module):
    """
    Baseline 1: Pure 1D Convolutional Network for spatial packet/flow features.
    """
    def __init__(self, num_features: int = 15, num_filters: int = 64):
        super().__init__()
        # Input shape: (Batch, Seq_len, Features) -> Transposed to (Batch, Features, Seq_len)
        self.conv1 = nn.Conv1d(in_channels=num_features, out_channels=num_filters, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(num_filters)
        self.conv2 = nn.Conv1d(in_channels=num_filters, out_channels=num_filters * 2, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(num_filters * 2)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc1 = nn.Linear(num_filters * 2, 64)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x):
        # x: (Batch, Seq_len, Features) -> (Batch, Features, Seq_len)
        x = x.transpose(1, 2)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.pool(x).squeeze(-1)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        out = self.fc2(x).squeeze(-1)
        return out

class StandaloneLSTM(nn.Module):
    """
    Baseline 2: Recurrent Long Short-Term Memory network for temporal sequence dynamics.
    """
    def __init__(self, num_features: int = 15, hidden_dim: int = 64, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=num_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0.0
        )
        self.fc1 = nn.Linear(hidden_dim, 32)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(32, 1)

    def forward(self, x):
        # x: (Batch, Seq_len, Features)
        lstm_out, (hn, _) = self.lstm(x)
        # Take the final step's hidden state
        last_hidden = hn[-1]
        x = F.relu(self.fc1(last_hidden))
        x = self.dropout(x)
        out = self.fc2(x).squeeze(-1)
        return out

class HybridCNNLSTM(nn.Module):
    """
    Paper 8 Proposed Architecture:
    1D-CNN extracts local spatial representations from network flow features,
    which are fed into an LSTM to learn temporal transitions and state changes over time.
    """
    def __init__(
        self, 
        num_features: int = 15, 
        cnn_filters: int = 64, 
        lstm_hidden: int = 64, 
        num_lstm_layers: int = 1
    ):
        super().__init__()
        # 1. Spatial Feature Extraction (Conv1D)
        self.conv1 = nn.Conv1d(
            in_channels=num_features, 
            out_channels=cnn_filters, 
            kernel_size=3, 
            padding=1
        )
        self.bn1 = nn.BatchNorm1d(cnn_filters)
        
        # 2. Temporal Sequence Modeling (LSTM)
        self.lstm = nn.LSTM(
            input_size=cnn_filters,
            hidden_size=lstm_hidden,
            num_layers=num_lstm_layers,
            batch_first=True,
            bidirectional=True
        )
        
        # 3. Dense Classifier Head
        lstm_output_dim = lstm_hidden * 2  # Bidirectional
        self.fc1 = nn.Linear(lstm_output_dim, 64)
        self.dropout = nn.Dropout(0.35)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x):
        # x shape: (Batch, Seq_len, Features)
        # Conv1D expects (Batch, Features, Seq_len)
        x_transposed = x.transpose(1, 2)
        c_out = F.relu(self.bn1(self.conv1(x_transposed)))
        
        # Transpose back to (Batch, Seq_len, cnn_filters) for LSTM
        lstm_in = c_out.transpose(1, 2)
        lstm_out, _ = self.lstm(lstm_in)
        
        # Global temporal pooling (max pooling over time steps)
        pooled, _ = torch.max(lstm_out, dim=1)
        
        # Classification head
        dense = F.relu(self.fc1(pooled))
        dense = self.dropout(dense)
        logits = self.fc2(dense).squeeze(-1)
        return logits

def format_graph_edge(
    src_ip: str, 
    dst_ip: str, 
    is_malicious: bool, 
    confidence_score: float, 
    protocol: str = "TCP",
    attack_category: str = "Botnet"
) -> dict:
    """
    Transforms model inference into a structured graph payload ready for Neo4j ingestion.
    """
    return {
        "source_node": {
            "label": "IPAddress",
            "properties": {"ip": src_ip, "type": "Host"}
        },
        "target_node": {
            "label": "IPAddress",
            "properties": {"ip": dst_ip, "type": "Server" if not is_malicious else "C2_Server"}
        },
        "relationship": {
            "type": "MALICIOUS_BOTNET_COMMUNICATION" if is_malicious else "NETWORK_COMMUNICATION",
            "properties": {
                "is_malicious": is_malicious,
                "confidence": round(float(confidence_score), 4),
                "protocol": protocol,
                "category": attack_category if is_malicious else "Benign"
            }
        }
    }
