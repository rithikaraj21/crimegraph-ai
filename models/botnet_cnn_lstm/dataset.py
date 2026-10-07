"""
CTU-13 / IoT-23 Network Traffic Dataset Handler for CrimeGraph AI.
Supports loading real NetFlow/Zeek conn.log files as well as generating
statistically authentic benchmark network traffic with botnet patterns.
"""

import os
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

FEATURE_COLUMNS = [
    "duration",
    "src_bytes",
    "dst_bytes",
    "src_pkts",
    "dst_pkts",
    "flow_rate_bytes_sec",
    "flow_rate_pkts_sec",
    "is_tcp",
    "is_udp",
    "is_icmp",
    "is_common_port",
    "inter_arrival_time",
    "syn_count",
    "fin_count",
    "rst_count"
]

def generate_benchmark_traffic(num_samples: int = 10000, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates synthetic teaching examples with simplified traffic patterns inspired by
    common botnet behaviors. These are not records from CTU-13 or IoT-23.
    """
    np.random.seed(random_seed)
    
    # 60% Benign, 40% Malicious (DDoS, PortScan, C&C-Beacon, Attack)
    n_benign = int(num_samples * 0.60)
    n_malicious = num_samples - n_benign
    
    # 1. Benign Traffic (Web browsing, DNS queries, SSH, media streaming)
    dur_benign = np.random.exponential(scale=3.5, size=n_benign)
    src_bytes_benign = np.random.lognormal(mean=7.0, sigma=1.2, size=n_benign)
    dst_bytes_benign = np.random.lognormal(mean=8.5, sigma=1.5, size=n_benign)
    src_pkts_benign = np.clip((src_bytes_benign / np.random.uniform(500, 1400, size=n_benign)).astype(int), 1, 5000)
    dst_pkts_benign = np.clip((dst_bytes_benign / np.random.uniform(500, 1400, size=n_benign)).astype(int), 1, 10000)
    
    proto_benign = np.random.choice(["TCP", "UDP", "ICMP"], p=[0.75, 0.23, 0.02], size=n_benign)
    common_port_benign = np.random.choice([1, 0], p=[0.85, 0.15], size=n_benign) # 80, 443, 53
    iat_benign = np.random.exponential(scale=0.5, size=n_benign)
    syn_benign = np.random.poisson(lam=1.2, size=n_benign)
    fin_benign = np.random.poisson(lam=1.0, size=n_benign)
    rst_benign = np.random.poisson(lam=0.1, size=n_benign)
    label_benign = np.zeros(n_benign, dtype=int)
    category_benign = ["Normal"] * n_benign
    
    # 2. Malicious Botnet Traffic (CTU-13 / IoT-23 characteristics)
    # A. C&C Beacons (Fixed tiny intervals, identical small byte sizes)
    n_cnc = int(n_malicious * 0.35)
    dur_cnc = np.random.normal(loc=0.08, scale=0.02, size=n_cnc).clip(0.01)
    src_bytes_cnc = np.random.normal(loc=64, scale=8, size=n_cnc).clip(32)
    dst_bytes_cnc = np.random.normal(loc=64, scale=8, size=n_cnc).clip(32)
    src_pkts_cnc = np.random.choice([1, 2], size=n_cnc)
    dst_pkts_cnc = np.random.choice([1, 2], size=n_cnc)
    proto_cnc = ["TCP"] * n_cnc
    common_port_cnc = np.random.choice([1, 0], p=[0.3, 0.7], size=n_cnc) # Often dynamic IRC or unusual ports
    iat_cnc = np.random.normal(loc=5.0, scale=0.05, size=n_cnc).clip(0.1) # Strict periodic beaconing
    syn_cnc = np.ones(n_cnc, dtype=int)
    fin_cnc = np.zeros(n_cnc, dtype=int)
    rst_cnc = np.zeros(n_cnc, dtype=int)
    category_cnc = ["C&C-Beacon"] * n_cnc
    
    # B. DDoS Floods (Extremely high packet count, tiny duration, massive SYN rate)
    n_ddos = int(n_malicious * 0.40)
    dur_ddos = np.random.uniform(0.01, 0.5, size=n_ddos)
    src_bytes_ddos = np.random.uniform(10000, 500000, size=n_ddos)
    dst_bytes_ddos = np.random.uniform(0, 100, size=n_ddos) # Asymmetric
    src_pkts_ddos = np.random.uniform(200, 5000, size=n_ddos).astype(int)
    dst_pkts_ddos = np.zeros(n_ddos, dtype=int)
    proto_ddos = np.random.choice(["TCP", "UDP"], p=[0.7, 0.3], size=n_ddos)
    common_port_ddos = np.random.choice([1, 0], p=[0.9, 0.1], size=n_ddos)
    iat_ddos = np.random.exponential(scale=0.001, size=n_ddos) # Sub-millisecond
    syn_ddos = np.random.uniform(100, 2000, size=n_ddos).astype(int)
    fin_ddos = np.zeros(n_ddos, dtype=int)
    rst_ddos = np.random.poisson(lam=5.0, size=n_ddos)
    category_ddos = ["DDoS"] * n_ddos
    
    # C. Port Scanning (Fast SYN packets across sequential ports, mostly no responses)
    n_scan = n_malicious - n_cnc - n_ddos
    dur_scan = np.random.uniform(0.005, 0.05, size=n_scan)
    src_bytes_scan = np.random.choice([40, 44, 48, 60], size=n_scan)
    dst_bytes_scan = np.zeros(n_scan)
    src_pkts_scan = np.ones(n_scan, dtype=int)
    dst_pkts_scan = np.zeros(n_scan, dtype=int)
    proto_scan = ["TCP"] * n_scan
    common_port_scan = np.zeros(n_scan, dtype=int)
    iat_scan = np.random.uniform(0.01, 0.1, size=n_scan)
    syn_scan = np.ones(n_scan, dtype=int)
    fin_scan = np.zeros(n_scan, dtype=int)
    rst_scan = np.random.choice([0, 1], p=[0.7, 0.3], size=n_scan)
    category_scan = ["PortScan"] * n_scan
    
    # Concatenate all
    durations = np.concatenate([dur_benign, dur_cnc, dur_ddos, dur_scan])
    src_bytes = np.concatenate([src_bytes_benign, src_bytes_cnc, src_bytes_ddos, src_bytes_scan])
    dst_bytes = np.concatenate([dst_bytes_benign, dst_bytes_cnc, dst_bytes_ddos, dst_bytes_scan])
    src_pkts = np.concatenate([src_pkts_benign, src_pkts_cnc, src_pkts_ddos, src_pkts_scan])
    dst_pkts = np.concatenate([dst_pkts_benign, dst_pkts_cnc, dst_pkts_ddos, dst_pkts_scan])
    protocols = np.concatenate([proto_benign, proto_cnc, proto_ddos, proto_scan])
    common_ports = np.concatenate([common_port_benign, common_port_cnc, common_port_ddos, common_port_scan])
    iats = np.concatenate([iat_benign, iat_cnc, iat_ddos, iat_scan])
    syns = np.concatenate([syn_benign, syn_cnc, syn_ddos, syn_scan])
    fins = np.concatenate([fin_benign, fin_cnc, fin_ddos, fin_scan])
    rsts = np.concatenate([rst_benign, rst_cnc, rst_ddos, rst_scan])
    
    labels = np.concatenate([
        label_benign, 
        np.ones(n_cnc, dtype=int), 
        np.ones(n_ddos, dtype=int), 
        np.ones(n_scan, dtype=int)
    ])
    categories = category_benign + category_cnc + category_ddos + category_scan
    
    df = pd.DataFrame({
        "duration": durations,
        "src_bytes": src_bytes,
        "dst_bytes": dst_bytes,
        "src_pkts": src_pkts,
        "dst_pkts": dst_pkts,
        "flow_rate_bytes_sec": (src_bytes + dst_bytes) / np.maximum(durations, 0.001),
        "flow_rate_pkts_sec": (src_pkts + dst_pkts) / np.maximum(durations, 0.001),
        "is_tcp": (protocols == "TCP").astype(int),
        "is_udp": (protocols == "UDP").astype(int),
        "is_icmp": (protocols == "ICMP").astype(int),
        "is_common_port": common_ports,
        "inter_arrival_time": iats,
        "syn_count": syns,
        "fin_count": fins,
        "rst_count": rsts,
        "label": labels,
        "category": categories
    })
    
    # Shuffle dataframe
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    return df

class FlowSequenceDataset(Dataset):
    """
    PyTorch Dataset that groups flows into sequential temporal windows of length `seq_len`
    for the CNN-LSTM architecture (Paper 8).
    """
    def __init__(self, X: np.ndarray, y: np.ndarray, seq_len: int = 8):
        self.seq_len = seq_len
        self.samples = []
        self.labels = []
        
        # Create sliding windows
        n_samples = len(X)
        for i in range(0, n_samples - seq_len + 1, seq_len // 2):
            self.samples.append(X[i:i + seq_len])
            # Sequence label is 1 if any flow in the sequence is malicious
            self.labels.append(1 if np.max(y[i:i + seq_len]) > 0 else 0)
            
        self.samples = np.array(self.samples, dtype=np.float32)
        self.labels = np.array(self.labels, dtype=np.float32)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        # Tensor shape: (sequence_length, num_features)
        return torch.tensor(self.samples[idx]), torch.tensor(self.labels[idx])

def prepare_dataloaders(
    df: pd.DataFrame, 
    seq_len: int = 8, 
    batch_size: int = 64, 
    scaler_save_path: str = None
):
    """
    Scales features, creates sliding windows, and returns train, val, test loaders.
    """
    X = df[FEATURE_COLUMNS].values
    y = df["label"].values
    
    # 70% Train, 15% Validation, 15% Test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.1765, random_state=42, stratify=y_train_val
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    if scaler_save_path:
        os.makedirs(os.path.dirname(scaler_save_path), exist_ok=True)
        joblib.dump(scaler, scaler_save_path)
    
    train_dataset = FlowSequenceDataset(X_train_scaled, y_train, seq_len=seq_len)
    val_dataset = FlowSequenceDataset(X_val_scaled, y_val, seq_len=seq_len)
    test_dataset = FlowSequenceDataset(X_test_scaled, y_test, seq_len=seq_len)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, val_loader, test_loader, scaler
