"""
Pre-Flight Checklist
Executable hardware calibration wizard.
Checks impedance, IMU, BLE/MAVLink handshake, baseline EEG.
"""

import time
import yaml
import numpy as np

from input.itie_bridge import ItieBridge
from transmission.mavlink_ble_sender import MavlinkBleSender
from safety.beta_drift_monitor import BetaDriftMonitor


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def run_checklist():
    cfg = load_config()
    sim = cfg.get("simulation_mode", True)
    results = {}

    print("\n" + "="*60)
    print("  Mind Link — Pre-Flight Checklist")
    print(f"  Mode: {'SIMULATION' if sim else 'HARDWARE'}")
    print("="*60 + "\n")

    bridge = ItieBridge(config=cfg)
    sender = MavlinkBleSender(config=cfg)

    # ------------------------------------------------------------------
    # Step 1: EEG Connection
    # ------------------------------------------------------------------
    print("[ 1/5 ] Connecting to itie headcap...")
    connected = bridge.connect()
    results["eeg_connected"] = connected
    _status(connected, "EEG headcap connected", "EEG connection failed")

    # ------------------------------------------------------------------
    # Step 2: Impedance Check
    # ------------------------------------------------------------------
    print("\n[ 2/5 ] Checking electrode impedance...")
    impedances = bridge.check_impedance()
    threshold = cfg["input"]["impedance_threshold_kohm"]
    bad = [ch for ch, v in impedances.items() if v > threshold]
    impedance_ok = len(bad) == 0
    results["impedance_ok"] = impedance_ok
    results["bad_channels"] = bad
    if impedance_ok:
        _status(True, f"All {len(impedances)} channels within {threshold} kΩ")
    else:
        _status(False, "", f"{len(bad)} channels exceed {threshold} kΩ: {bad}")
        print("  → Please re-seat electrodes on bad channels before flight")

    # ------------------------------------------------------------------
    # Step 3: IMU Calibration
    # ------------------------------------------------------------------
    print("\n[ 3/5 ] Calibrating IMU...")
    bridge.start_stream()
    time.sleep(1.0)
    window = bridge.get_window(int(cfg["input"]["sample_rate"] * 2))
    imu_ok = False
    if window is not None:
        imu = window["imu"]
        # Check quaternion norm ≈ 1
        norms = np.linalg.norm(imu, axis=1)
        imu_ok = bool(np.abs(norms.mean() - 1.0) < 0.1)
        results["imu_norm_mean"] = float(norms.mean())
    results["imu_ok"] = imu_ok
    _status(imu_ok, f"IMU calibrated (quaternion norm ≈ {results.get('imu_norm_mean', 0):.3f})",
            "IMU calibration failed — check sensor connection")

    # ------------------------------------------------------------------
    # Step 4: BLE + MAVLink Handshake
    # ------------------------------------------------------------------
    print("\n[ 4/5 ] Testing transmission link...")
    link_ok = sender.connect()
    results["link_ok"] = link_ok
    results["active_link"] = sender._active_link
    _status(link_ok, f"Link established ({sender._active_link})", "No transmission link available")

    # ------------------------------------------------------------------
    # Step 5: Baseline EEG Recording
    # ------------------------------------------------------------------
    print("\n[ 5/5 ] Recording baseline EEG (eyes open — 5 seconds)...")
    print("  → Please sit still and look straight ahead")
    time.sleep(1.0)

    baseline_window = bridge.get_window(int(cfg["input"]["sample_rate"] * 5))
    baseline_ok = baseline_window is not None
    results["baseline_ok"] = baseline_ok

    if baseline_ok:
        monitor = BetaDriftMonitor(config=cfg)
        monitor.calibrate_baseline(baseline_window["eeg"])
        results["baseline_beta"] = monitor._baseline_beta
        _status(True, f"Baseline recorded (beta power: {monitor._baseline_beta:.4f} μV²/Hz)")
    else:
        _status(False, "", "Baseline recording failed — insufficient data")

    bridge.stop_stream()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print("  Pre-Flight Checklist Summary")
    print("="*60)
    all_ok = all([
        results.get("eeg_connected"),
        results.get("impedance_ok"),
        results.get("imu_ok"),
        results.get("link_ok"),
        results.get("baseline_ok")
    ])

    for key, val in results.items():
        icon = "✓" if val is True else ("✗" if val is False else "→")
        print(f"  {icon} {key}: {val}")

    print()
    if all_ok:
        print("  ✅ ALL CHECKS PASSED — Safe to fly")
    else:
        print("  ❌ SOME CHECKS FAILED — Do NOT fly until resolved")
    print("="*60 + "\n")

    return all_ok, results


def _status(ok: bool, success_msg: str = "", fail_msg: str = ""):
    if ok:
        print(f"  ✓ {success_msg}")
    else:
        print(f"  ✗ {fail_msg}")


if __name__ == "__main__":
    run_checklist()
