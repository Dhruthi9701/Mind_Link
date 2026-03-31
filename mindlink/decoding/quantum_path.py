"""
Unit 3 – Decoding Unit: Quantum Path
ZZFeatureMap (reps=2, linear entanglement) + QSVM via Qiskit.
Target circuit depth ≤ 30 after transpile(optimization_level=3).
"""

import time
import numpy as np
import yaml
from pathlib import Path

try:
    from qiskit.circuit.library import ZZFeatureMap
    from qiskit_machine_learning.algorithms import QSVC
    from qiskit_aer import AerSimulator
    from qiskit import transpile
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("[quantum_path] Qiskit not found — quantum path disabled")


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class QuantumDecoder:
    """
    QSVM-based EEG decoder using ZZFeatureMap quantum kernel.
    Falls back gracefully if Qiskit unavailable.
    """

    def __init__(self, config: dict = None):
        self.cfg = config or load_config()
        self.n_qubits = self.cfg["decoding"]["n_qubits"]
        self.reps = self.cfg["decoding"]["feature_map_reps"]
        self.entanglement = self.cfg["decoding"]["entanglement"]
        self.max_depth = self.cfg["decoding"]["max_circuit_depth"]
        self.available = QISKIT_AVAILABLE
        self.model = None
        self.feature_map = None
        self._last_latency_ms = 0.0

        if self.available:
            self._build_feature_map()

    def _build_feature_map(self):
        """Build and transpile ZZFeatureMap circuit."""
        self.feature_map = ZZFeatureMap(
            feature_dimension=self.n_qubits,
            reps=self.reps,
            entanglement=self.entanglement
        )
        # Transpile to check depth
        backend = AerSimulator()
        transpiled = transpile(self.feature_map, backend=backend, optimization_level=3)
        depth = transpiled.depth()
        print(f"[quantum_path] ZZFeatureMap circuit depth: {depth} (target ≤ {self.max_depth})")
        if depth > self.max_depth:
            print(f"[quantum_path] ⚠ Circuit depth {depth} exceeds target {self.max_depth}")

        # Visualize circuit
        try:
            fig = self.feature_map.decompose().draw("mpl")
            fig.savefig("mindlink/quantum_circuit.png", dpi=80, bbox_inches="tight")
            print("[quantum_path] Circuit diagram saved to mindlink/quantum_circuit.png")
        except Exception:
            print(self.feature_map.draw("text"))

    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """
        Train QSVM on feature vectors normalized to [0, π].

        Args:
            X_train: (n_samples, n_qubits) feature matrix
            y_train: (n_samples,) class labels
        """
        if not self.available:
            print("[quantum_path] Qiskit unavailable — skipping quantum training")
            return

        print(f"[quantum_path] Training QSVM on {X_train.shape[0]} samples...")
        print(f"[quantum_path] This may take 5-10 minutes (computing {X_train.shape[0]}x{X_train.shape[0]} quantum kernel matrix)...")
        t0 = time.time()

        # Ensure features match qubit count
        X_train = self._prepare_features(X_train)

        self.model = QSVC(quantum_kernel=self._build_kernel())
        self.model.fit(X_train, y_train)

        elapsed = (time.time() - t0) * 1000
        print(f"[quantum_path] QSVM training complete in {elapsed:.0f} ms")

    def _build_kernel(self):
        """Build quantum kernel from feature map."""
        from qiskit_machine_learning.kernels import FidelityQuantumKernel
        return FidelityQuantumKernel(feature_map=self.feature_map)

    def predict(self, features: np.ndarray):
        """
        Run quantum inference.

        Returns:
            (predicted_class, confidence, latency_ms)
        """
        if not self.available or self.model is None:
            return -1, 0.0, 0.0

        t0 = time.time()
        x = self._prepare_features(features.reshape(1, -1))

        try:
            pred = self.model.predict(x)[0]
            # Confidence via decision function if available
            try:
                scores = self.model.decision_function(x)[0]
                confidence = float(np.max(np.abs(scores)) / (np.sum(np.abs(scores)) + 1e-9))
            except Exception:
                confidence = 0.8  # default if not available

            latency_ms = (time.time() - t0) * 1000
            self._last_latency_ms = latency_ms
            print(f"[quantum_path] Prediction: class={pred}, conf={confidence:.2f}, latency={latency_ms:.1f} ms")
            return int(pred), float(confidence), latency_ms

        except Exception as e:
            print(f"[quantum_path] Inference error: {e}")
            return -1, 0.0, (time.time() - t0) * 1000

    def _prepare_features(self, X: np.ndarray) -> np.ndarray:
        """Ensure feature vector has exactly n_qubits dimensions."""
        n = self.n_qubits
        if X.shape[-1] >= n:
            return X[..., :n]
        # Pad with zeros if too short
        pad = np.zeros((*X.shape[:-1], n - X.shape[-1]))
        return np.concatenate([X, pad], axis=-1)

    def save(self, path: str = None):
        """Serialize trained model."""
        import pickle
        if path is None:
            path = Path(__file__).parent.parent / "models" / "quantum_model.pkl"
        else:
            path = Path(path)
            
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"[quantum_path] Model saved to {path}")

    def load(self, path: str = None):
        """Load serialized model."""
        import pickle
        if path is None:
            path = Path(__file__).parent.parent / "models" / "quantum_model.pkl"
        else:
            path = Path(path)
            
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        print(f"[quantum_path] Model loaded from {path}")
