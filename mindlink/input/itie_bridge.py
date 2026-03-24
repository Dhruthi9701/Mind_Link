"""
Unit 1 – Input Unit: itie Full Headcap Bridge
Handles LSL primary stream + raw TCP socket fallback.
Streams raw μV EEG + IMU quaternions into BrainFlow buffer.
"""

import time
import socket
import threading
import numpy as np
import yaml
from pathlib import Path

# Optional imports — graceful fallback in simulation mode
try:
    from pylsl import StreamInlet, resolve_stream
    LSL_AVAILABLE = True
except ImportError:
    LSL_AVAILABLE = False
    print("[itie_bridge] pylsl not found — simulation mode only")

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
    BRAINFLOW_AVAILABLE = True
except ImportError:
    BRAINFLOW_AVAILABLE = False
    print("[itie_bridge] BrainFlow not found — simulation mode only")


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class ItieBridge:
    """
    Manages connection to itie 32/64-channel EEG headcap.
    Primary: LSL stream. Fallback: raw TCP socket.
    Simulation mode: generates synthetic EEG + IMU data.
    """

    def __init__(self, config: dict = None):
        self.cfg = config or load_config()
        self.sim_mode = self.cfg.get("simulation_mode", True)
        self.n_channels = self.cfg["input"]["n_channels"]
        self.sample_rate = self.cfg["input"]["sample_rate"]
        self.buffer: list = []
        self._running = False
        self._lock = threading.Lock()
        self._inlet = None
        self._sock = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Auto-connect wizard: tries LSL → TCP → simulation."""
        if self.sim_mode:
            print("[itie_bridge] Simulation mode active — synthetic data")
            return True

        if LSL_AVAILABLE and self._try_lsl():
            print("[itie_bridge] Connected via LSL")
            return True

        if self._try_tcp():
            print("[itie_bridge] Connected via TCP fallback")
            return True

        print("[itie_bridge] No hardware found — falling back to simulation")
        self.sim_mode = True
        return True

    def _try_lsl(self) -> bool:
        try:
            print("[itie_bridge] Searching for LSL stream...")
            streams = resolve_stream("name", self.cfg["input"]["lsl_stream_name"], timeout=3.0)
            if streams:
                self._inlet = StreamInlet(streams[0])
                return True
        except Exception as e:
            print(f"[itie_bridge] LSL failed: {e}")
        return False

    def _try_tcp(self) -> bool:
        try:
            host = self.cfg["input"]["tcp_host"]
            port = self.cfg["input"]["tcp_port"]
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(3.0)
            self._sock.connect((host, port))
            return True
        except Exception as e:
            print(f"[itie_bridge] TCP failed: {e}")
        return False

    # ------------------------------------------------------------------
    # Impedance check
    # ------------------------------------------------------------------

    def check_impedance(self) -> dict:
        """
        Returns per-channel impedance in kΩ.
        Simulation returns random values around threshold.
        """
        threshold = self.cfg["input"]["impedance_threshold_kohm"]
        if self.sim_mode:
            impedances = {
                f"ch{i}": round(np.random.uniform(1.0, threshold * 1.5), 2)
                for i in range(self.n_channels)
            }
        else:
            # Real hardware: send impedance query command
            impedances = self._query_hardware_impedance()

        bad_channels = [ch for ch, val in impedances.items() if val > threshold]
        if bad_channels:
            print(f"[itie_bridge] ⚠ High impedance channels: {bad_channels}")
        else:
            print("[itie_bridge] ✓ All channels within impedance threshold")
        return impedances

    def _query_hardware_impedance(self) -> dict:
        """Placeholder for real hardware impedance query."""
        return {f"ch{i}": 2.5 for i in range(self.n_channels)}

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def start_stream(self):
        """Start background thread to fill buffer."""
        self._running = True
        t = threading.Thread(target=self._stream_loop, daemon=True)
        t.start()
        print("[itie_bridge] Streaming started")

    def stop_stream(self):
        self._running = False
        if self._sock:
            self._sock.close()
        print("[itie_bridge] Streaming stopped")

    def _stream_loop(self):
        while self._running:
            sample = self._get_sample()
            with self._lock:
                self.buffer.append(sample)
                # Keep rolling buffer of last 2 seconds
                max_samples = int(self.sample_rate * self.cfg["input"]["buffer_size_seconds"])
                if len(self.buffer) > max_samples:
                    self.buffer = self.buffer[-max_samples:]
            time.sleep(1.0 / self.sample_rate)

    def _get_sample(self) -> dict:
        """Get one sample: EEG (n_channels,) + IMU quaternion (4,)."""
        if self.sim_mode:
            return self._simulate_sample()
        elif self._inlet:
            sample, _ = self._inlet.pull_sample()
            eeg = np.array(sample[:self.n_channels])
            imu = np.array(sample[self.n_channels:self.n_channels + 4]) if len(sample) > self.n_channels else np.array([1, 0, 0, 0], dtype=float)
            return {"eeg": eeg, "imu": imu, "timestamp": time.time()}
        elif self._sock:
            return self._read_tcp_sample()
        return self._simulate_sample()

    def _simulate_sample(self) -> dict:
        """Synthetic EEG: pink noise + alpha/beta oscillations."""
        t = time.time()
        eeg = np.random.randn(self.n_channels) * 10.0  # μV
        # Add synthetic mu rhythm on C3/C4 (channels 7, 11)
        eeg[7] += 15 * np.sin(2 * np.pi * 10 * t)
        eeg[11] += 15 * np.sin(2 * np.pi * 10 * t + np.pi / 4)
        imu = np.array([1.0, 0.01 * np.random.randn(), 0.01 * np.random.randn(), 0.01 * np.random.randn()])
        return {"eeg": eeg, "imu": imu, "timestamp": t}

    def _read_tcp_sample(self) -> dict:
        """Read raw bytes from TCP socket and parse EEG + IMU."""
        try:
            n_bytes = (self.n_channels + 4) * 4  # float32
            data = b""
            while len(data) < n_bytes:
                chunk = self._sock.recv(n_bytes - len(data))
                if not chunk:
                    break
                data += chunk
            arr = np.frombuffer(data, dtype=np.float32)
            eeg = arr[:self.n_channels].astype(float)
            imu = arr[self.n_channels:self.n_channels + 4].astype(float)
            return {"eeg": eeg, "imu": imu, "timestamp": time.time()}
        except Exception as e:
            print(f"[itie_bridge] TCP read error: {e}")
            return self._simulate_sample()

    # ------------------------------------------------------------------
    # Buffer access
    # ------------------------------------------------------------------

    def get_window(self, n_samples: int):
        """Return latest n_samples as numpy arrays."""
        with self._lock:
            if len(self.buffer) < n_samples:
                return None
            window = self.buffer[-n_samples:]
        eeg = np.stack([s["eeg"] for s in window])   # (n_samples, n_channels)
        imu = np.stack([s["imu"] for s in window])   # (n_samples, 4)
        return {"eeg": eeg, "imu": imu}
