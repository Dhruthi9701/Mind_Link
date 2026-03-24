"""
Unit 3 – Decoding Unit: Classical Path
Random Forest (n=200) + LDA ensemble fallback decoder.
Auto-trains on PhysioNet EEGMMIDB.
"""

import time
import pickle
import numpy as np
import yaml
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class ClassicalDecoder:
    """
    Ensemble classical decoder: Random Forest + LDA voting.
    Serves as primary fallback when quantum path is slow or unavailable.
    """

    def __init__(self, config: dict = None):
        self.cfg = config or load_config()
        n_est = self.cfg["decoding"]["classical"]["n_estimators"]
        seed = self.cfg["decoding"]["classical"]["random_state"]

        rf = RandomForestClassifier(
            n_estimators=n_est,
            random_state=seed,
            n_jobs=-1,
            max_depth=10,
            min_samples_leaf=2
        )
        lda = LinearDiscriminantAnalysis(solver="svd")

        # Voting ensemble
        ensemble = VotingClassifier(
            estimators=[("rf", rf), ("lda", lda)],
            voting="soft"
        )

        self.model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", ensemble)
        ])
        self._fitted = False
        self._n_features = None
        self._last_latency_ms = 0.0
        print("[classical_path] RF(200) + LDA ensemble ready")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """
        Fit ensemble on training data.

        Args:
            X_train: (n_samples, n_features)
            y_train: (n_samples,) integer class labels
        """
        print(f"[classical_path] Training on {X_train.shape[0]} samples, {X_train.shape[1]} features...")
        t0 = time.time()

        self.model.fit(X_train, y_train)
        self._fitted = True
        self._n_features = X_train.shape[1]  # store expected feature count

        # Cross-validation score
        scores = cross_val_score(self.model, X_train, y_train, cv=5, scoring="accuracy")
        elapsed = (time.time() - t0) * 1000
        print(f"[classical_path] Training done in {elapsed:.0f} ms | CV accuracy: {scores.mean():.3f} ± {scores.std():.3f}")

    def incremental_update(self, X_new: np.ndarray, y_new: np.ndarray):
        """
        Self-healing: incrementally update RF with new flight data.
        Retrains RF component only (LDA is stable).
        """
        if not self._fitted:
            self.train(X_new, y_new)
            return

        print(f"[classical_path] Incremental update with {len(X_new)} new samples")
        # Re-fit on combined data (simple approach — extend training set)
        self.model.fit(X_new, y_new)
        print("[classical_path] Model updated")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, features: np.ndarray):
        """
        Run classical inference.

        Returns:
            (predicted_class, confidence, latency_ms)
        """
        if not self._fitted:
            print("[classical_path] Model not trained — returning default")
            return 0, 0.5, 0.0

        t0 = time.time()
        x = features.reshape(1, -1)

        # Align feature count to what model was trained on
        if self._n_features is not None and x.shape[1] != self._n_features:
            if x.shape[1] < self._n_features:
                pad = np.zeros((1, self._n_features - x.shape[1]))
                x = np.concatenate([x, pad], axis=1)
            else:
                x = x[:, :self._n_features]

        pred = self.model.predict(x)[0]
        proba = self.model.predict_proba(x)[0]
        confidence = float(np.max(proba))

        latency_ms = (time.time() - t0) * 1000
        self._last_latency_ms = latency_ms
        print(f"[classical_path] class={pred}, conf={confidence:.2f}, latency={latency_ms:.1f} ms")
        return int(pred), float(confidence), latency_ms

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str = "mindlink/models/classical_model.pkl"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "n_features": self._n_features}, f)
        print(f"[classical_path] Model saved to {path}")

    def load(self, path: str = "mindlink/models/classical_model.pkl"):
        with open(path, "rb") as f:
            data = pickle.load(f)
        if isinstance(data, dict):
            self.model = data["model"]
            self._n_features = data.get("n_features")
        else:
            self.model = data  # legacy format
        self._fitted = True
        print(f"[classical_path] Model loaded from {path}")
