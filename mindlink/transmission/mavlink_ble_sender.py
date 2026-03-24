"""
Unit 4 – Transmission Unit: MAVLink 2.0 + BLE Dual-Link Sender
Primary: 5G URLLC / Wi-Fi MAVLink. Fallback: BLE via bleak.
Target packet assembly latency < 20 ms.
"""

import time
import struct
import asyncio
import threading
import numpy as np
import yaml
from pathlib import Path

try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False
    print("[mavlink_ble] pymavlink not found — simulation mode")

try:
    from bleak import BleakClient, BleakScanner
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False
    print("[mavlink_ble] bleak not found — BLE disabled")

# MAVLink command mapping
INTENT_TO_CMD = {
    0: {"pitch": 5.0,  "yaw": 0.0,   "roll": 0.0,  "alt": 0.0},   # Forward
    1: {"pitch": -5.0, "yaw": 0.0,   "roll": 0.0,  "alt": 0.0},   # Backward
    2: {"pitch": 0.0,  "yaw": -10.0, "roll": -5.0, "alt": 0.0},   # Left
    3: {"pitch": 0.0,  "yaw": 10.0,  "roll": 5.0,  "alt": 0.0},   # Right
    -1: {"pitch": 0.0, "yaw": 0.0,   "roll": 0.0,  "alt": 0.0},   # Hover
}


def load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class MavlinkBleSender:
    """
    Dual-link command sender.
    Encodes intent → MAVLink 2.0 packet → sends via 5G/WiFi or BLE fallback.
    """

    def __init__(self, config: dict = None):
        self.cfg = config or load_config()
        self.sim_mode = self.cfg.get("simulation_mode", True)
        self.max_latency = self.cfg["transmission"]["max_latency_ms"]
        self._mav_conn = None
        self._ble_client = None
        self._ble_loop = None
        self._active_link = None
        self._packet_count = 0

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Try MAVLink primary → BLE fallback → simulation."""
        if self.sim_mode:
            print("[mavlink_ble] Simulation mode — no hardware connection")
            self._active_link = "simulation"
            return True

        if MAVLINK_AVAILABLE and self._try_mavlink():
            self._active_link = "mavlink"
            return True

        if BLE_AVAILABLE and self._try_ble():
            self._active_link = "ble"
            return True

        print("[mavlink_ble] No link available — simulation fallback")
        self._active_link = "simulation"
        return True

    def _try_mavlink(self) -> bool:
        try:
            baud = self.cfg["transmission"]["mavlink_baud"]
            self._mav_conn = mavutil.mavlink_connection("/dev/ttyUSB0", baud=baud)
            self._mav_conn.wait_heartbeat(timeout=3)
            print(f"[mavlink_ble] MAVLink connected (system {self._mav_conn.target_system})")
            return True
        except Exception as e:
            print(f"[mavlink_ble] MAVLink failed: {e}")
            return False

    def _try_ble(self) -> bool:
        try:
            device_name = self.cfg["transmission"]["ble_device_name"]
            self._ble_loop = asyncio.new_event_loop()
            t = threading.Thread(target=self._ble_loop.run_forever, daemon=True)
            t.start()
            future = asyncio.run_coroutine_threadsafe(
                self._ble_connect(device_name), self._ble_loop
            )
            result = future.result(timeout=5.0)
            if result:
                print(f"[mavlink_ble] BLE connected to {device_name}")
            return result
        except Exception as e:
            print(f"[mavlink_ble] BLE failed: {e}")
            return False

    async def _ble_connect(self, device_name: str) -> bool:
        devices = await BleakScanner.discover(timeout=3.0)
        for d in devices:
            if d.name and device_name in d.name:
                self._ble_client = BleakClient(d.address)
                await self._ble_client.connect()
                return True
        return False

    # ------------------------------------------------------------------
    # Send command
    # ------------------------------------------------------------------

    def send_intent(self, intent: int, confidence: float) -> float:
        """
        Encode intent → MAVLink packet → transmit.

        Args:
            intent: 0-3 (Forward/Backward/Left/Right) or -1 (Hover)
            confidence: decoder confidence score

        Returns:
            transmission_latency_ms
        """
        t0 = time.time()

        cmd = INTENT_TO_CMD.get(intent, INTENT_TO_CMD[-1])
        packet = self._encode_mavlink(cmd, confidence)

        if self._active_link == "mavlink":
            self._send_mavlink(cmd)
        elif self._active_link == "ble":
            self._send_ble(packet)
        else:
            self._simulate_send(cmd)

        latency_ms = (time.time() - t0) * 1000
        self._packet_count += 1

        if latency_ms > self.max_latency:
            print(f"[mavlink_ble] ⚠ Latency {latency_ms:.1f} ms exceeds target {self.max_latency} ms")
        else:
            print(f"[mavlink_ble] Sent packet #{self._packet_count} | {latency_ms:.1f} ms | link={self._active_link}")

        return latency_ms

    def send_hover(self):
        """Emergency hover command."""
        print("[mavlink_ble] 🛑 HOVER command sent")
        self.send_intent(-1, 1.0)

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def _encode_mavlink(self, cmd: dict, confidence: float) -> bytes:
        """
        Encode command as MAVLink 2.0 style binary packet.
        Returns raw bytes for BLE fallback.
        """
        seq = self._packet_count & 0xFF
        # Header: magic(B) + len(H) + seq(B) + sys(B) + comp(B) + msg_id(B)
        header = struct.pack(">BHBBBB", 0xFD, 20, seq, 1, 1, 82)
        # Payload: pitch, yaw, roll, alt, confidence (5 floats)
        payload = struct.pack(">fffff",
            cmd["pitch"], cmd["yaw"], cmd["roll"], cmd["alt"], confidence)
        return header + payload

    def _send_mavlink(self, cmd: dict):
        """Send via pymavlink connection."""
        try:
            self._mav_conn.mav.set_attitude_target_send(
                int(time.time() * 1000) & 0xFFFFFFFF,
                self._mav_conn.target_system,
                self._mav_conn.target_component,
                0b00000111,  # type_mask: ignore body rates
                [1, 0, 0, 0],  # quaternion (identity)
                0, 0, 0,       # body roll/pitch/yaw rates
                0.5            # thrust
            )
        except Exception as e:
            print(f"[mavlink_ble] Send error: {e}")

    def _send_ble(self, packet: bytes):
        """Send packet via BLE characteristic."""
        if self._ble_client and self._ble_loop:
            CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
            future = asyncio.run_coroutine_threadsafe(
                self._ble_client.write_gatt_char(CHAR_UUID, packet),
                self._ble_loop
            )
            future.result(timeout=0.05)

    def _simulate_send(self, cmd: dict):
        """Simulate transmission with realistic delay."""
        time.sleep(0.005)  # 5 ms simulated network delay
        print(f"[mavlink_ble] [SIM] pitch={cmd['pitch']:.1f} yaw={cmd['yaw']:.1f} roll={cmd['roll']:.1f}")

    def disconnect(self):
        if self._mav_conn:
            self._mav_conn.close()
        if self._ble_client and self._ble_loop:
            asyncio.run_coroutine_threadsafe(
                self._ble_client.disconnect(), self._ble_loop
            ).result(timeout=2.0)
        print("[mavlink_ble] Disconnected")
