"""
Unit 5 – Safety Unit: Beta-Wave Drift Monitor
Monitors 13-30 Hz power in sliding 5s window.
>25% drop → GPS Hover + voice alert + classical-only mode.
Triple-redundant kill-switch.
"""

import time
import threading
import numpy as np
import yaml
from pathlib import Path
from collections import deque
from scipy.signal import welch

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class BetaDriftMonitor:
    """
    Monitors pilot cognitive state via beta-band EEG power.
    Triggers safety responses on fatigue detection.
    """

    def __init__(self, config: dict = None, sender=None, decoder=None):
        self.cfg = config or load_config()
        self.fs = self.cfg["input"]["sample_rate"]
        self.beta_low = self.cfg["safety"]["beta_band_low"]
        self.beta_high = self.cfg["safety"]["beta_band_high"]
        self.window_s = self.cfg["safety"]["drift_window_seconds"]
        self.threshold_pct = self.cfg["safety"]["drift_threshold_percent"]

        self.sender = sender    # MavlinkBleSender reference
        self.decoder = decoder  # HybridDecoder reference

        # Rolling buffer of beta power measurements
        self._beta_history = deque(maxlen=100)
        self._baseline_beta = None
        self._kill_switch_active = False
        self._quantum_kill = False
        self._classical_kill = False
        self._manual_kill = False

        # TTS engine
        self._tts = None
        if TTS_AVAILABLE:
            try:
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", 180)
            except Exception:
                pass

        print(f"[beta_monitor] Beta drift monitor ready ({self.beta_low}-{self.beta_high} Hz, threshold={self.threshold_pct}%)")

    # ------------------------------------------------------------------
    # Baseline calibration
    # ------------------------------------------------------------------

    def calibrate_baseline(self, eeg_window: np.ndarray):
        """Record baseline beta power (eyes open, resting)."""
        beta_power = self._compute_beta_power(eeg_window)
        self._baseline_beta = beta_power
        print(f"[beta_monitor] Baseline beta power: {beta_power:.4f} μV²/Hz")

    # ------------------------------------------------------------------
    # Main monitoring
    # ------------------------------------------------------------------

    def update(self, eeg_window: np.ndarray) -> dict:
        """
        Process new EEG window and check for fatigue.

        Args:
            eeg_window: (n_samples, n_channels)

        Returns:
            status dict with fatigue flag and beta power
        """
        beta_power = self._compute_beta_power(eeg_window)
        self._beta_history.append(beta_power)

        if self._baseline_beta is None:
            self._baseline_beta = beta_power
            return {"fatigue": False, "beta_power": beta_power, "drift_pct": 0.0}

        drift_pct = ((self._baseline_beta - beta_power) / (self._baseline_beta + 1e-9)) * 100.0
        fatigue_detected = drift_pct > self.threshold_pct

        status = {
            "fatigue": fatigue_detected,
            "beta_power": beta_power,
            "baseline_beta": self._baseline_beta,
            "drift_pct": drift_pct,
            "kill_active": self._kill_switch_active
        }

        if fatigue_detected and not self._kill_switch_active:
            print(f"[beta_monitor] ⚠ FATIGUE DETECTED — beta drift {drift_pct:.1f}% > {self.threshold_pct}%")
            self._trigger_safety_response()

        return status

    # ------------------------------------------------------------------
    # Safety responses
    # ------------------------------------------------------------------

    def _trigger_safety_response(self):
        """Full safety response: hover + alert + classical-only."""
        self._kill_switch_active = True

        # 1. Send hover command
        if self.sender:
            self.sender.send_hover()

        # 2. Voice alert
        self._voice_alert("Warning: Pilot fatigue detected. Activating GPS hover.")

        # 3. Switch to classical-only mode
        if self.decoder and hasattr(self.decoder, "_use_quantum"):
            self.decoder._use_quantum = False
            print("[beta_monitor] Switched to classical-only mode")

        print("[beta_monitor] 🛑 Safety response complete")

    def _voice_alert(self, message: str):
        """Text-to-speech alert."""
        print(f"[beta_monitor] 🔊 ALERT: {message}")
        if self._tts:
            try:
                self._tts.say(message)
                self._tts.runAndWait()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Kill switches (triple redundant)
    # ------------------------------------------------------------------

    def kill_quantum(self):
        """Kill switch 1: disable quantum path."""
        self._quantum_kill = True
        if self.decoder:
            self.decoder._use_quantum = False
        print("[beta_monitor] Kill switch 1: Quantum path disabled")

    def kill_classical(self):
        """Kill switch 2: disable classical path (emergency only)."""
        self._classical_kill = True
        print("[beta_monitor] Kill switch 2: Classical path disabled — HOVER ONLY")
        if self.sender:
            self.sender.send_hover()

    def manual_kill(self):
        """Kill switch 3: manual emergency stop."""
        self._manual_kill = True
        self._kill_switch_active = True
        print("[beta_monitor] Kill switch 3: MANUAL EMERGENCY STOP")
        self._voice_alert("Emergency stop activated.")
        if self.sender:
            self.sender.send_hover()

    def reset(self):
        """Reset kill switches after pilot recovery."""
        self._kill_switch_active = False
        self._quantum_kill = False
        self._classical_kill = False
        self._manual_kill = False
        if self.decoder:
            self.decoder._use_quantum = True
        print("[beta_monitor] Kill switches reset — resuming normal operation")

    # ------------------------------------------------------------------
    # Beta power computation
    # ------------------------------------------------------------------

    def _compute_beta_power(self, eeg: np.ndarray) -> float:
        """
        Compute mean beta band power across all channels.
        Uses Welch PSD estimate.
        """
        powers = []
        for ch in range(eeg.shape[1]):
            freqs, psd = welch(eeg[:, ch], fs=self.fs, nperseg=min(128, len(eeg)))
            beta_mask = (freqs >= self.beta_low) & (freqs <= self.beta_high)
            if beta_mask.any():
                powers.append(np.mean(psd[beta_mask]))
        return float(np.mean(powers)) if powers else 0.0

    @property
    def is_safe(self) -> bool:
        """True if no kill switch is active."""
        return not self._kill_switch_active
