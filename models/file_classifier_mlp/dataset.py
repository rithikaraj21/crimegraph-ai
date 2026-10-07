"""
Govdocs1 Digital Evidence Dataset Handler for CrimeGraph AI (Paper 5).
Generates and handles forensic file fragments (byte sequences, magic numbers,
header signatures, and textual n-grams) for file-type identification.
"""

import os
import glob
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

FILE_CATEGORIES = [
    "PDF_DOCUMENT",
    "OFFICE_DOCX",
    "JPEG_IMAGE",
    "EXECUTABLE_PAYLOAD",
    "TEXT_LOG",
    "ARCHIVE_ZIP"
]

def generate_benchmark_govdocs(num_samples: int = 6000, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates synthetic file fragments with common format-signature tokens.
    These are teaching examples, not fragments sampled from the Govdocs1 corpus.
    """
    np.random.seed(random_seed)
    samples_per_class = num_samples // len(FILE_CATEGORIES)
    
    records = []
    
    # Signatures and typical structural tokens
    signatures = {
        "PDF_DOCUMENT": [
            "25 50 44 46 2d", "2f 54 79 70 65", "2f 43 61 74 61 6c 6f 67", "6f 62 6a", "65 6e 64 6f 62 6a",
            "73 74 72 65 61 6d", "65 6e 64 73 74 72 65 61 6d", "78 72 65 66", "74 72 61 69 6c 65 72", "25 25 45 4f 46"
        ],
        "OFFICE_DOCX": [
            "50 4b 03 04", "14 00 06 00", "77 6f 72 64 2f 64 6f 63 75 6d 65 6e 74 2e 78 6d 6c",
            "5b 43 6f 6e 74 65 6e 74 5f 54 79 70 65 73 5d 2e 78 6d 6c", "50 4b 01 02", "50 4b 05 06",
            "72 65 6c 73 2f 2e 72 65 6c 73", "77 6f 72 64 2f 73 74 79 6c 65 73 2e 78 6d 6c"
        ],
        "JPEG_IMAGE": [
            "ff d8 ff e0", "00 10 4a 46 49 46 00 01", "ff db 00 43", "ff c0 00 11", "08 02",
            "ff c4 00 1f", "ff da 00 0c", "03 01 00 02", "ff d9", "e2 8a 28 a2"
        ],
        "EXECUTABLE_PAYLOAD": [
            "4d 5a 90 00", "50 45 00 00", "7f 45 4c 46", "02 01 01 00", "2e 74 65 78 74",
            "2e 64 61 74 61", "2e 72 73 72 63", "8b 45 f4 89", "55 89 e5 83", "c3 e8 00 00"
        ],
        "TEXT_LOG": [
            "5b 49 4e 46 4f 5d", "5b 45 52 52 4f 52 5d", "32 30 32 36 2d", "55 53 45 52 5f", "4c 4f 47 49 4e",
            "41 55 54 48 5f", "46 41 49 4c", "50 41 53 53 57 44", "49 50 3d 31 39 32", "53 45 53 53 49 4f 4e"
        ],
        "ARCHIVE_ZIP": [
            "50 4b 03 04", "0a 00 00 00", "00 00", "50 4b 07 08", "50 4b 01 02", "50 4b 05 06",
            "64 61 74 61 2e 62 69 6e", "73 65 63 72 65 74 2e 74 78 74", "70 61 73 73 77 64"
        ]
    }
    
    for cat in FILE_CATEGORIES:
        pool = signatures[cat]
        for i in range(samples_per_class):
            # Synthesize realistic forensic sector sequence
            # Choose a combination of signature tokens plus randomized byte tokens
            n_tokens = np.random.randint(12, 30)
            chosen_sig_tokens = list(np.random.choice(pool, size=np.random.randint(5, 12), replace=True))
            
            # Add general byte noise tokens
            noise_tokens = [f"{np.random.randint(0, 256):02x}" for _ in range(n_tokens - len(chosen_sig_tokens))]
            
            # Combine and shuffle slightly to mimic non-contiguous carving
            all_tokens = chosen_sig_tokens + noise_tokens
            np.random.shuffle(all_tokens)
            
            # Prepend header magic bytes for 70% of fragments (representing file headers)
            if np.random.rand() > 0.3:
                all_tokens.insert(0, pool[0])
                
            token_string = " ".join(all_tokens)
            records.append({
                "fragment_id": f"{cat[:3].lower()}_{i:05d}",
                "content": token_string,
                "label": cat
            })
            
    df = pd.DataFrame(records)
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    return df

def load_govdocs_dataset(data_dir: str = None, num_samples: int = 6000):
    """
    Reads simple local file chunks only when a directory is explicitly supplied;
    otherwise generates synthetic Govdocs1-style examples for the demo.
    """
    if data_dir and os.path.exists(data_dir) and len(glob.glob(os.path.join(data_dir, "*.*"))) > 50:
        print(f"[*] Found local Govdocs1 files in {data_dir}. Processing raw files...")
        # Local raw file reading logic
        records = []
        for fpath in glob.glob(os.path.join(data_dir, "*.*"))[:num_samples]:
            ext = os.path.splitext(fpath)[1].lower().replace(".", "")
            try:
                with open(fpath, "rb") as f:
                    chunk = f.read(512)
                    hex_str = " ".join(f"{b:02x}" for b in chunk)
                    records.append({
                        "fragment_id": os.path.basename(fpath),
                        "content": hex_str,
                        "label": ext.upper()
                    })
            except Exception:
                continue
        if len(records) > 100:
            df = pd.DataFrame(records)
            return df
            
    return generate_benchmark_govdocs(num_samples=num_samples)
