"""
Unit 3 – Decoding Unit: Hybrid Auto-Switch Logic
Runs quantum + classical in parallel. Auto-switches based on latency + confidence.
Returns 4-class intent: 0=Forward, 1=Backward, 2=Left, 3=Right
"""

import time
import threading
import numpy as np
import yaml
from pathlib import Path
from .quantum_path import QuantumDecoder
from .classical_path import ClassicalDecoder

INTENT_LABELS = {0: "Forward", 1: "Backward", 2: "Left", 3: "Right"}


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class HybridDecoder:
    """
    Parallel quantum + classical inference with auto-fallback.
    Quantum is preferred when latency < 100 ms AND confidence ≥ 0.75.
    """

    def __init__(self, config: dict = None):
        self.cfg = config or load_config()
        self.q_timeout = self.cfg["decoding"]["quantum_timeout_ms"]
        self.conf_threshold = self.cfg["decoding"]["confidence_threshold"]

        self.quantum = QuantumDecoder(config=self.cfg)
        self.classical = ClassicalDecoder(config=self.cfg)

        self._use_quantum = True
        self._quantum_fail_count = 0
        self._loop_count = 0
        print("[hybrid_decoder] Hybrid decoder initialized")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """Train both paths."""
        print("[hybrid_decoder] Training classical path...")
        self.classical.train(X_train, y_train)

        print("[hybrid_decoder] Training quantum path...")
        self.quantum.train(X_train, y_train)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, features: np.ndarray) -> dict:
        """
        Run hybrid inference.

        Returns dict with:
            intent (int), label (str), confidence (float),
            path_used (str), latency_ms (float)
        """
        t0 = time.time()
        self._loop_count += 1

        # Run quantum in thread with timeout
        q_result = {"pred": -1, "conf": 0.0, "latency": 9999.0}
        c_result = {"pred": 0, "conf": 0.5, "latency": 0.0}

        # Always run classical (fast baseline)
        c_pred, c_conf, c_lat = self.classical.predict(features)
        c_result = {"pred": c_pred, "conf": c_conf, "latency": c_lat}

        # Try quantum if enabled
        if self._use_quantum and self.quantum.available and self.quantum.model is not None:
            q_thread_result = [None]

            def run_quantum():
                q_thread_result[0] = self.quantum.predict(features)

            t = threading.Thread(target=run_quantum)
            t.start()
            t.join(timeout=self.q_timeout / 1000.0)

            if t.is_alive() or q_thread_result[0] is None:
                print(f"[hybrid_decoder] Quantum timeout (>{self.q_timeout} ms) — using classical")
                self._quantum_fail_count += 1
            else:
                q_pred, q_conf, q_lat = q_thread_result[0]
                q_result = {"pred": q_pred, "conf": q_conf, "latency": q_lat}

        # Decision logic
        use_quantum = (
            q_result["pred"] != -1
            and q_result["latency"] < self.q_timeout
            and q_result["conf"] >= self.conf_threshold
        )

        if use_quantum:
            final_pred = q_result["pred"]
            final_conf = q_result["conf"]
            path_used = "quantum"
        else:
            final_pred = c_result["pred"]
            final_conf = c_result["conf"]
            path_used = "classical"

        # Disable quantum after 3 consecutive failures
        if self._quantum_fail_count >= 3:
            if self._use_quantum:
                print("[hybrid_decoder] Quantum path disabled after repeated failures")
            self._use_quantum = False

        total_latency = (time.time() - t0) * 1000
        label = INTENT_LABELS.get(final_pred, "Unknown")

        result = {
            "intent": final_pred,
            "label": label,
            "confidence": final_conf,
            "path_used": path_used,
            "latency_ms": total_latency,
            "quantum_latency_ms": q_result["latency"],
            "classical_latency_ms": c_result["latency"]
        }

        print(f"[hybrid_decoder] → {label} | conf={final_conf:.2f} | path={path_used} | {total_latency:.1f} ms")
        return result

    def incremental_update(self, X_new: np.ndarray, y_new: np.ndarray):
        """Self-healing: update classical model with new flight data."""
        self.classical.incremental_update(X_new, y_new)

    def save_models(self):
        self.quantum.save()
        self.classical.save()

    def load_models(self):
        try:
            self.quantum.load()
        except Exception as e:
            print(f"[hybrid_decoder] Quantum model load failed: {e}")
        try:
            self.classical.load()
        except Exception as e:
            print(f"[hybrid_decoder] Classical model load failed: {e}")
