"""
Unit Tests — Full Pipeline Coverage
Tests every critical component.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
import yaml

# Load test config (simulation mode)
with open(os.path.join(os.path.dirname(__file__), "..", "config.yaml")) as f:
    CFG = yaml.safe_load(f)
CFG["simulation_mode"] = True


# ------------------------------------------------------------------
# Unit 1: Input
# ------------------------------------------------------------------

class TestItieBridge:
    def setup_method(self):
        from input.itie_bridge import ItieBridge
        self.bridge = ItieBridge(config=CFG)

    def test_connect_simulation(self):
        assert self.bridge.connect() is True

    def test_impedance_check_returns_dict(self):
        self.bridge.connect()
        imp = self.bridge.check_impedance()
        assert isinstance(imp, dict)
        assert len(imp) == CFG["input"]["n_channels"]

    def test_simulate_sample_shape(self):
        sample = self.bridge._simulate_sample()
        assert sample["eeg"].shape == (CFG["input"]["n_channels"],)
        assert sample["imu"].shape == (4,)

    def test_stream_and_get_window(self):
        import time
        self.bridge.connect()
        self.bridge.start_stream()
        time.sleep(0.5)
        n = int(CFG["input"]["sample_rate"] * 0.2)
        window = self.bridge.get_window(n)
        self.bridge.stop_stream()
        assert window is not None
        assert window["eeg"].shape[1] == CFG["input"]["n_channels"]


# ------------------------------------------------------------------
# Unit 2: Processing
# ------------------------------------------------------------------

class TestDenoisingPipeline:
    def setup_method(self):
        from processing.denoising_pipeline import DenoisingPipeline
        self.pipeline = DenoisingPipeline(config=CFG)
        self.fs = CFG["input"]["sample_rate"]
        self.n_ch = CFG["input"]["n_channels"]
        self.n_samples = int(self.fs * 0.5)

    def _make_data(self):
        eeg = np.random.randn(self.n_samples, self.n_ch) * 10.0
        imu = np.tile([1, 0, 0, 0], (self.n_samples, 1)).astype(float)
        return eeg, imu

    def test_output_is_1d(self):
        eeg, imu = self._make_data()
        features = self.pipeline.process(eeg, imu)
        assert features.ndim == 1

    def test_features_normalized_to_pi(self):
        eeg, imu = self._make_data()
        features = self.pipeline.process(eeg, imu)
        assert features.min() >= -1e-6
        assert features.max() <= np.pi + 1e-6

    def test_bandpass_filter(self):
        eeg = np.random.randn(self.n_samples, self.n_ch)
        filtered = self.pipeline._apply_bandpass(eeg)
        assert filtered.shape == eeg.shape

    def test_imu_artifact_cancel(self):
        eeg = np.random.randn(self.n_samples, self.n_ch)
        imu = np.random.randn(self.n_samples, 4)
        cleaned = self.pipeline._imu_artifact_cancel(eeg, imu)
        assert cleaned.shape == eeg.shape


# ------------------------------------------------------------------
# Unit 3: Decoding
# ------------------------------------------------------------------

class TestClassicalDecoder:
    def setup_method(self):
        from decoding.classical_path import ClassicalDecoder
        self.decoder = ClassicalDecoder(config=CFG)
        self.n_features = 20

    def _make_training_data(self, n=100):
        X = np.random.rand(n, self.n_features) * np.pi
        y = np.random.randint(0, 4, n)
        return X, y

    def test_train_and_predict(self):
        X, y = self._make_training_data()
        self.decoder.train(X, y)
        pred, conf, lat = self.decoder.predict(X[0])
        assert pred in [0, 1, 2, 3]
        assert 0.0 <= conf <= 1.0
        assert lat >= 0.0

    def test_incremental_update(self):
        X, y = self._make_training_data()
        self.decoder.train(X, y)
        X_new, y_new = self._make_training_data(20)
        self.decoder.incremental_update(X_new, y_new)
        pred, conf, _ = self.decoder.predict(X_new[0])
        assert pred in [0, 1, 2, 3]


class TestHybridDecoder:
    def setup_method(self):
        from decoding.hybrid_decoder import HybridDecoder
        self.decoder = HybridDecoder(config=CFG)
        X = np.random.rand(80, 20) * np.pi
        y = np.array([i % 4 for i in range(80)])
        self.decoder.classical.train(X, y)

    def test_predict_returns_valid_result(self):
        features = np.random.rand(20) * np.pi
        result = self.decoder.predict(features)
        assert "intent" in result
        assert "label" in result
        assert "confidence" in result
        assert "path_used" in result
        assert result["intent"] in [0, 1, 2, 3]

    def test_fallback_to_classical_when_quantum_unavailable(self):
        self.decoder._use_quantum = False
        features = np.random.rand(20) * np.pi
        result = self.decoder.predict(features)
        assert result["path_used"] == "classical"


# ------------------------------------------------------------------
# Unit 4: Transmission
# ------------------------------------------------------------------

class TestMavlinkBleSender:
    def setup_method(self):
        from transmission.mavlink_ble_sender import MavlinkBleSender
        self.sender = MavlinkBleSender(config=CFG)
        self.sender.connect()

    def test_connect_simulation(self):
        assert self.sender._active_link == "simulation"

    def test_send_intent_returns_latency(self):
        lat = self.sender.send_intent(0, 0.9)
        assert lat >= 0.0

    def test_send_hover(self):
        # Should not raise
        self.sender.send_hover()

    def test_encode_packet(self):
        cmd = {"pitch": 5.0, "yaw": 0.0, "roll": 0.0, "alt": 0.0}
        packet = self.sender._encode_mavlink(cmd, 0.9)
        assert isinstance(packet, bytes)
        assert len(packet) > 0


# ------------------------------------------------------------------
# Unit 5: Safety
# ------------------------------------------------------------------

class TestBetaDriftMonitor:
    def setup_method(self):
        from safety.beta_drift_monitor import BetaDriftMonitor
        self.monitor = BetaDriftMonitor(config=CFG)
        self.fs = CFG["input"]["sample_rate"]
        self.n_ch = CFG["input"]["n_channels"]

    def _make_eeg(self, beta_scale=1.0):
        n = int(self.fs * 2)
        eeg = np.random.randn(n, self.n_ch) * 5.0
        t = np.linspace(0, 2, n)
        for ch in range(self.n_ch):
            eeg[:, ch] += beta_scale * 10 * np.sin(2 * np.pi * 20 * t)
        return eeg

    def test_calibrate_baseline(self):
        eeg = self._make_eeg()
        self.monitor.calibrate_baseline(eeg)
        assert self.monitor._baseline_beta > 0

    def test_no_fatigue_on_stable_signal(self):
        eeg = self._make_eeg(beta_scale=1.0)
        self.monitor.calibrate_baseline(eeg)
        status = self.monitor.update(eeg)
        assert status["fatigue"] is False

    def test_fatigue_on_dropped_beta(self):
        eeg_baseline = self._make_eeg(beta_scale=1.0)
        self.monitor.calibrate_baseline(eeg_baseline)
        eeg_fatigued = self._make_eeg(beta_scale=0.1)  # 90% drop
        status = self.monitor.update(eeg_fatigued)
        assert status["fatigue"] is True

    def test_triple_kill_switches(self):
        self.monitor.kill_quantum()
        assert self.monitor._quantum_kill is True
        self.monitor.kill_classical()
        assert self.monitor._classical_kill is True
        self.monitor.manual_kill()
        assert self.monitor._manual_kill is True
        self.monitor.reset()
        assert self.monitor._kill_switch_active is False


# ------------------------------------------------------------------
# Feature Engineering
# ------------------------------------------------------------------

class TestFeatureEngineering:
    def test_normalize_to_pi(self):
        from utils.feature_engineering import normalize_to_pi
        X = np.random.randn(50, 10) * 100
        X_norm = normalize_to_pi(X)
        assert X_norm.min() >= -1e-6
        assert X_norm.max() <= np.pi + 1e-6

    def test_synthetic_physionet(self):
        from utils.feature_engineering import _synthetic_physionet
        X, y = _synthetic_physionet(n_epochs=20)
        assert X.shape[0] == 20
        assert len(y) == 20

    def test_welch_psd_features(self):
        from utils.feature_engineering import extract_welch_psd_features
        X = np.random.randn(10, 32, 640)
        feats = extract_welch_psd_features(X, fs=250.0)
        assert feats.shape[0] == 10
        assert feats.min() >= -1e-6


# ------------------------------------------------------------------
# Latency Benchmark
# ------------------------------------------------------------------

class TestLatencyBenchmark:
    def test_record_and_report(self):
        from utils.latency_benchmark import LatencyBenchmark
        bench = LatencyBenchmark(target_ms=150.0, log_interval=5)
        for i in range(10):
            bench.record_e2e(float(50 + i * 5))
        p95 = bench.get_p95()
        assert p95 > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
