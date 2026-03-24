"""
Feature Engineering Utilities
PhysioNet EEGMMIDB download, CSP extraction, Welch PSD, normalization.
"""

import numpy as np
import yaml
from pathlib import Path

try:
    import mne
    from mne.datasets import eegbci
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False
    print("[feature_eng] MNE not available — synthetic data only")

try:
    from mne.decoding import CSP
    CSP_AVAILABLE = True
except ImportError:
    CSP_AVAILABLE = False


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def download_physionet(subject: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """
    Download PhysioNet EEGMMIDB for given subject.
    Motor imagery runs: 4 (left fist), 8 (right fist), 12 (both fists/feet).

    Returns:
        X: (n_epochs, n_channels, n_times)
        y: (n_epochs,) labels 0-3
    """
    if not MNE_AVAILABLE:
        print("[feature_eng] MNE not available — generating synthetic PhysioNet data")
        return _synthetic_physionet()

    print(f"[feature_eng] Downloading PhysioNet Subject {subject}...")
    runs = [4, 8, 12]  # Motor imagery runs
    raw_files = eegbci.load_data(subject, runs, path="mindlink/data/physionet/")

    raws = [mne.io.read_raw_edf(f, preload=True, stim_channel="auto") for f in raw_files]
    raw = mne.concatenate_raws(raws)

    # Standardize channel names
    mne.datasets.eegbci.standardize(raw)
    raw.set_montage("standard_1005")

    # Bandpass filter
    raw.filter(8.0, 30.0, fir_design="firwin", skip_by_annotation="edge")

    # Extract epochs
    events, event_id = mne.events_from_annotations(raw)
    picks = mne.pick_types(raw.info, meg=False, eeg=True, stim=False, eog=False)

    epochs = mne.Epochs(
        raw, events, event_id,
        tmin=-1.0, tmax=4.0,
        proj=True, picks=picks,
        baseline=None, preload=True
    )

    X = epochs.get_data()  # (n_epochs, n_channels, n_times)
    y = epochs.events[:, -1] - 1  # 0-indexed labels

    print(f"[feature_eng] Loaded {X.shape[0]} epochs, {X.shape[1]} channels")
    return X, y


def _synthetic_physionet(n_epochs: int = 200, n_channels: int = 32, n_times: int = 640) -> tuple:
    """Generate synthetic EEG data mimicking PhysioNet structure."""
    print(f"[feature_eng] Generating {n_epochs} synthetic epochs...")
    X = np.random.randn(n_epochs, n_channels, n_times) * 10.0
    # Add class-specific patterns
    for i in range(n_epochs):
        label = i % 4
        freq = [10, 12, 8, 15][label]
        t = np.linspace(0, 2.56, n_times)
        X[i, 7] += 20 * np.sin(2 * np.pi * freq * t)   # C3
        X[i, 11] += 20 * np.sin(2 * np.pi * freq * t)  # C4
    y = np.array([i % 4 for i in range(n_epochs)])
    return X, y


def extract_csp_features(X: np.ndarray, y: np.ndarray, n_components: int = 4) -> np.ndarray:
    """
    Extract CSP (Common Spatial Patterns) features.

    Args:
        X: (n_epochs, n_channels, n_times)
        y: (n_epochs,) labels

    Returns:
        features: (n_epochs, n_components * 2)
    """
    if not CSP_AVAILABLE:
        print("[feature_eng] CSP not available — using variance features")
        return X.var(axis=-1)

    csp = CSP(n_components=n_components, reg=None, log=True, norm_trace=False)
    features = csp.fit_transform(X, y)
    print(f"[feature_eng] CSP features: {features.shape}")
    return features


def extract_welch_psd_features(X: np.ndarray, fs: float = 250.0) -> np.ndarray:
    """
    Extract Welch PSD features for mu and beta bands.
    C3 (ch 7) and C4 (ch 11) + neighbors.

    Args:
        X: (n_epochs, n_channels, n_times)
        fs: sampling frequency

    Returns:
        features: (n_epochs, n_features) normalized to [0, π]
    """
    from scipy.signal import welch

    # Focus channels: C3, C4 and neighbors
    focus_channels = [5, 6, 7, 8, 9, 10, 11, 12]
    focus_channels = [c for c in focus_channels if c < X.shape[1]]

    features_list = []
    for epoch in X:
        epoch_feats = []
        for ch in focus_channels:
            freqs, psd = welch(epoch[ch], fs=fs, nperseg=min(256, epoch.shape[-1]))
            mu_mask = (freqs >= 8) & (freqs <= 13)
            beta_mask = (freqs >= 13) & (freqs <= 30)
            epoch_feats.append(np.mean(psd[mu_mask]) if mu_mask.any() else 0.0)
            epoch_feats.append(np.mean(psd[beta_mask]) if beta_mask.any() else 0.0)
        features_list.append(epoch_feats)

    features = np.array(features_list)
    return normalize_to_pi(features)


def normalize_to_pi(features: np.ndarray) -> np.ndarray:
    """Normalize feature matrix to [0, π] per feature."""
    f_min = features.min(axis=0)
    f_max = features.max(axis=0)
    denom = f_max - f_min
    denom[denom == 0] = 1.0
    return (features - f_min) / denom * np.pi


def add_imu_features(features: np.ndarray, imu_data: np.ndarray) -> np.ndarray:
    """
    Append IMU quaternion mean as 4 extra features.

    Args:
        features: (n_epochs, n_features)
        imu_data: (n_epochs, 4) or (4,) mean quaternion

    Returns:
        (n_epochs, n_features + 4)
    """
    if imu_data.ndim == 1:
        imu_tiled = np.tile(imu_data, (features.shape[0], 1))
    else:
        imu_tiled = imu_data[:features.shape[0]]

    return np.concatenate([features, imu_tiled], axis=1)


def prepare_training_data(subject: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """
    Full pipeline: download → CSP + PSD features → normalize → add IMU.

    Returns:
        X_features: (n_epochs, n_features) normalized to [0, π]
        y: (n_epochs,) labels
    """
    cfg = load_config()
    X_raw, y = download_physionet(subject)

    # CSP features
    csp_feats = extract_csp_features(X_raw, y, n_components=4)

    # Welch PSD features
    psd_feats = extract_welch_psd_features(X_raw, fs=cfg["input"]["sample_rate"])

    # Combine
    X_combined = np.concatenate([csp_feats, psd_feats], axis=1)

    # Add synthetic IMU (zeros for training data)
    imu_zeros = np.zeros((X_combined.shape[0], 4))
    X_final = add_imu_features(X_combined, imu_zeros)

    # Final normalization
    X_final = normalize_to_pi(X_final)

    print(f"[feature_eng] Final feature matrix: {X_final.shape}, labels: {np.unique(y)}")
    return X_final, y
