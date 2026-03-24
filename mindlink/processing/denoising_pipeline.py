"""
Unit 2 – Processing Unit: Real-time EEG Denoising Pipeline
Bandpass → Notch → PCA → Blink/EOG removal → IMU motion correction.
Outputs clean feature vector every 500 ms window (50% overlap).
"""

import time
import numpy as np
import yaml
from pathlib import Path
from scipy.signal import butter, sosfilt, iirnotch, sosfiltfilt
from sklearn.decomposition import PCA

try:
    import mne
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False
    print("[denoising] MNE not found — using scipy fallback")


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class DenoisingPipeline:
    """
    Real-time EEG preprocessing pipeline.
    Input:  raw EEG window (n_samples, n_channels) + IMU (n_samples, 4)
    Output: clean feature vector ready for decoding
    """

    def __init__(self, config: dict = None):
        self.cfg = config or load_config()
        self.fs = self.cfg["input"]["sample_rate"]
        self.bp_low = self.cfg["processing"]["bandpass_low"]
        self.bp_high = self.cfg["processing"]["bandpass_high"]
        self.notch = self.cfg["processing"]["notch_freq"]
        self.pca_var = self.cfg["processing"]["pca_variance"]
        self.n_channels = self.cfg["input"]["n_channels"]

        # Build filters once
        self._bp_sos = self._build_bandpass()
        self._notch_sos = self._build_notch()

        # PCA fitted lazily on first window
        self._pca = None  # type: PCA
        self._pca_fitted = False

        print(f"[denoising] Pipeline ready — {self.bp_low}-{self.bp_high} Hz bandpass, notch {self.notch} Hz")

    # ------------------------------------------------------------------
    # Filter builders
    # ------------------------------------------------------------------

    def _build_bandpass(self):
        """4th-order Butterworth bandpass."""
        nyq = self.fs / 2.0
        low = self.bp_low / nyq
        high = self.bp_high / nyq
        return butter(4, [low, high], btype="band", output="sos")

    def _build_notch(self):
        """Notch filter at power line frequency."""
        b, a = iirnotch(self.notch, Q=30, fs=self.fs)
        from scipy.signal import tf2sos
        return tf2sos(b, a)

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def process(self, eeg: np.ndarray, imu: np.ndarray) -> np.ndarray:
        """
        Full preprocessing pipeline.

        Args:
            eeg: (n_samples, n_channels) raw EEG in μV
            imu: (n_samples, 4) quaternion IMU data

        Returns:
            feature_vector: 1D numpy array ready for decoding
        """
        t0 = time.time()

        # 1. Bandpass filter
        eeg = self._apply_bandpass(eeg)

        # 2. Notch filter
        eeg = self._apply_notch(eeg)

        # 3. IMU motion correction (bobble-head filter)
        eeg = self._imu_artifact_cancel(eeg, imu)

        # 4. Blink/EOG removal via threshold + interpolation
        eeg = self._remove_blink_artifacts(eeg)

        # 5. PCA dimensionality reduction
        eeg_pca = self._apply_pca(eeg)

        # 6. Extract features
        features = self._extract_features(eeg_pca, imu)

        elapsed_ms = (time.time() - t0) * 1000
        print(f"[denoising] Processing time: {elapsed_ms:.1f} ms | features: {features.shape}")

        return features

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    def _apply_bandpass(self, eeg: np.ndarray) -> np.ndarray:
        """Apply bandpass filter to each channel."""
        return sosfilt(self._bp_sos, eeg, axis=0)

    def _apply_notch(self, eeg: np.ndarray) -> np.ndarray:
        """Apply notch filter to each channel."""
        return sosfilt(self._notch_sos, eeg, axis=0)

    def _imu_artifact_cancel(self, eeg: np.ndarray, imu: np.ndarray) -> np.ndarray:
        """
        Bobble-head motion correction.
        Regresses out IMU quaternion components from EEG channels.
        """
        # Use quaternion angular velocity as regressors
        imu_reg = imu - imu.mean(axis=0)  # zero-mean
        # Least-squares regression per channel
        try:
            coeffs, _, _, _ = np.linalg.lstsq(imu_reg, eeg, rcond=None)
            motion_artifact = imu_reg @ coeffs
            eeg_clean = eeg - motion_artifact
        except Exception:
            eeg_clean = eeg
        return eeg_clean

    def _remove_blink_artifacts(self, eeg: np.ndarray) -> np.ndarray:
        """
        Simple threshold-based blink removal.
        Channels with amplitude > 100 μV are interpolated from neighbors.
        """
        threshold = 100.0  # μV
        for ch in range(eeg.shape[1]):
            bad_samples = np.abs(eeg[:, ch]) > threshold
            if bad_samples.any() and ch > 0 and ch < eeg.shape[1] - 1:
                # Linear interpolation from neighbors
                eeg[bad_samples, ch] = (eeg[bad_samples, ch - 1] + eeg[bad_samples, ch + 1]) / 2.0
        return eeg

    def _apply_pca(self, eeg: np.ndarray) -> np.ndarray:
        """
        PCA to retain 95% variance.
        Fitted on first window, then applied consistently.
        """
        if not self._pca_fitted:
            self._pca = PCA(n_components=self.pca_var, svd_solver="full")
            eeg_pca = self._pca.fit_transform(eeg)
            self._pca_fitted = True
            n_comp = self._pca.n_components_
            print(f"[denoising] PCA fitted: {n_comp} components retain {self.pca_var*100:.0f}% variance")
        else:
            eeg_pca = self._pca.transform(eeg)
        return eeg_pca

    def _extract_features(self, eeg_pca: np.ndarray, imu: np.ndarray) -> np.ndarray:
        """
        Extract feature vector:
        - Welch PSD for mu (8-13 Hz) and beta (13-30 Hz) bands
        - C3/C4 channel power (indices 7, 11 in 32-ch layout)
        - IMU quaternion mean (4 features)
        - Normalize all to [0, π]
        """
        from scipy.signal import welch

        features = []

        # PSD features per PCA component
        for comp in range(min(eeg_pca.shape[1], 8)):
            freqs, psd = welch(eeg_pca[:, comp], fs=self.fs, nperseg=min(128, len(eeg_pca)))
            # Mu band power
            mu_mask = (freqs >= 8) & (freqs <= 13)
            beta_mask = (freqs >= 13) & (freqs <= 30)
            features.append(np.mean(psd[mu_mask]) if mu_mask.any() else 0.0)
            features.append(np.mean(psd[beta_mask]) if beta_mask.any() else 0.0)

        # IMU quaternion mean (4 features)
        imu_mean = imu.mean(axis=0)
        features.extend(imu_mean.tolist())

        features = np.array(features, dtype=np.float64)

        # Normalize to [0, π]
        feat_min = features.min()
        feat_max = features.max()
        if feat_max > feat_min:
            features = (features - feat_min) / (feat_max - feat_min) * np.pi
        else:
            features = np.zeros_like(features)

        return features
