"""
Full Model Training Script
Trains quantum circuit + classical ensemble on PhysioNet EEGMMIDB.
Target: ≥ 82% accuracy on Subject 1.
"""

import time
import numpy as np
import yaml
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from utils.feature_engineering import prepare_training_data
from decoding.hybrid_decoder import HybridDecoder


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def train(subject: int = None):
    cfg = load_config()
    subject = subject or cfg["decoding"]["physionet_subject"]

    print(f"\n{'='*60}")
    print(f"Mind Link — Training Pipeline (Subject {subject})")
    print(f"{'='*60}\n")

    # 1. Prepare data
    print("[train] Preparing training data...")
    X, y = prepare_training_data(subject=subject)
    print(f"[train] Dataset: {X.shape[0]} samples, {X.shape[1]} features, {len(np.unique(y))} classes")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"[train] Train: {len(X_train)}, Test: {len(X_test)}")

    # 2. Train hybrid decoder
    decoder = HybridDecoder(config=cfg)

    t0 = time.time()
    print("\n[train] Note: Quantum training can take 5-10 minutes...")
    print("[train] Tip: Press Ctrl+C to skip quantum and use classical only\n")
    
    try:
        decoder.train(X_train, y_train)
    except KeyboardInterrupt:
        print("\n[train] Quantum training interrupted - using classical only")
        decoder.quantum.available = False
    
    train_time = time.time() - t0
    print(f"\n[train] Total training time: {train_time:.1f} s")

    # 3. Evaluate classical path
    print("\n[train] Evaluating classical path...")
    y_pred_classical = []
    for x in X_test:
        pred, conf, _ = decoder.classical.predict(x)
        y_pred_classical.append(pred)

    acc_classical = accuracy_score(y_test, y_pred_classical)
    print(f"[train] Classical accuracy: {acc_classical:.3f}")
    
    # Get actual class names based on unique labels
    unique_classes = sorted(np.unique(y_test))
    class_names = ["Left Fist", "Right Fist", "Both Fists", "Rest"]
    target_names = [class_names[i] for i in unique_classes]
    
    print(classification_report(y_test, y_pred_classical,
                                labels=unique_classes,
                                target_names=target_names,
                                zero_division=0))

    if acc_classical >= 0.82:
        print(f"[train] ✓ Target accuracy ≥ 82% achieved: {acc_classical:.1%}")
    else:
        print(f"[train] ⚠ Accuracy {acc_classical:.1%} below 82% target — consider more data")

    # 4. Evaluate quantum path (if available)
    if decoder.quantum.available and decoder.quantum.model is not None:
        print("\n[train] Evaluating quantum path (sample of 20)...")
        sample_idx = np.random.choice(len(X_test), min(20, len(X_test)), replace=False)
        y_pred_q = []
        for i in sample_idx:
            pred, conf, _ = decoder.quantum.predict(X_test[i])
            y_pred_q.append(pred)
        acc_q = accuracy_score(y_test[sample_idx], y_pred_q)
        print(f"[train] Quantum accuracy (n=20): {acc_q:.3f}")

    # 5. Save models
    print("\n[train] Saving models...")
    decoder.save_models()
    print("[train] ✓ Models saved")

    return decoder, acc_classical


if __name__ == "__main__":
    import sys
    subject = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    train(subject=subject)
