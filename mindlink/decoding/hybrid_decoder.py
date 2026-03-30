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
        Run hybrid inference in parallel.
        """
        t0 = time.time()
        self._loop_count += 1

        results = {}
        
        def run_classical():
            try:
                pred, conf, lat = self.classical.predict(features)
                results["classical"] = {"pred": pred, "conf": conf, "latency": lat}
            except Exception as e:
                print(f"[hybrid_decoder] Classical path error: {e}")
                results["classical"] = {"pred": 0, "conf": 0.0, "latency": 0.0}

        def run_quantum():
            try:
                if self._use_quantum and self.quantum.available and self.quantum.model is not None:
                    pred, conf, lat = self.quantum.predict(features)
                    results["quantum"] = {"pred": pred, "conf": conf, "latency": lat}
                else:
                    results["quantum"] = {"pred": -1, "conf": 0.0, "latency": 9999.0}
            except Exception as e:
                print(f"[hybrid_decoder] Quantum path error: {e}")
                results["quantum"] = {"pred": -1, "conf": 0.0, "latency": 9999.0}

        # Start both in parallel
        t_c = threading.Thread(target=run_classical)
        t_q = threading.Thread(target=run_quantum)
        
        t_c.start()
        t_q.start()

        # Wait for classical (should be very fast)
        t_c.join()
        
        # Wait for quantum with timeout
        t_q.join(timeout=self.q_timeout / 1000.0)

        q_res = results.get("quantum", {"pred": -1, "conf": 0.0, "latency": 9999.0})
        c_res = results.get("classical", {"pred": 0, "conf": 0.5, "latency": 0.0})

        if t_q.is_alive():
            print(f"[hybrid_decoder] Quantum timeout (>{self.q_timeout} ms) — using classical")
            self._quantum_fail_count += 1
            path_used = "classical"
            final_pred, final_conf = c_res["pred"], c_res["conf"]
        else:
            # Decision logic: Quantum preferred if confident
            use_quantum = (
                q_res["pred"] != -1
                and q_res["conf"] >= self.conf_threshold
            )
            if use_quantum:
                final_pred, final_conf = q_res["pred"], q_res["conf"]
                path_used = "quantum"
                self._quantum_fail_count = 0 # reset on success
            else:
                final_pred, final_conf = c_res["pred"], c_res["conf"]
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
            "quantum_latency_ms": q_res["latency"],
            "classical_latency_ms": c_res["latency"]
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
