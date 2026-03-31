"""
Real-Time Inference Loop
Live BCI → decode → transmit with hardware simulation mode.
Logs end-to-end latency every loop.
"""

import time
import yaml
import numpy as np
from pathlib import Path

from input.itie_bridge import ItieBridge
from processing.denoising_pipeline import DenoisingPipeline
from decoding.hybrid_decoder import HybridDecoder
from transmission.mavlink_ble_sender import MavlinkBleSender
from safety.beta_drift_monitor import BetaDriftMonitor
from utils.latency_benchmark import LatencyBenchmark


def load_config():
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def run():
    cfg = load_config()
    sim = cfg.get("simulation_mode", True)
    fs = cfg["input"]["sample_rate"]
    window_ms = cfg["processing"]["window_size_ms"]
    overlap = cfg["processing"]["window_overlap"]
    n_samples = int(fs * window_ms / 1000)
    step_samples = int(n_samples * (1 - overlap))
    step_time_s = step_samples / fs
    adaptive_interval = cfg["safety"]["adaptive_update_interval_seconds"]

    print(f"\n{'='*60}")
    print("Mind Link — Real-Time Inference")
    print(f"Mode: {'SIMULATION' if sim else 'HARDWARE'}")
    print(f"Window: {window_ms} ms ({n_samples} samples), overlap: {overlap*100:.0f}%")
    print(f"{'='*60}\n")

    # Initialize all units
    bridge = ItieBridge(config=cfg)
    pipeline = DenoisingPipeline(config=cfg)
    decoder = HybridDecoder(config=cfg)
    sender = MavlinkBleSender(config=cfg)
    monitor = BetaDriftMonitor(config=cfg, sender=sender, decoder=decoder)
    bench = LatencyBenchmark(
        target_ms=cfg["latency"]["target_e2e_ms"],
        log_interval=cfg["latency"]["log_interval"]
    )

    # Connect hardware
    bridge.connect()
    sender.connect()

    # Load pre-trained models
    decoder.load_models()

    # Auto-train models if not found
    if not decoder.classical._fitted:
        print("[inference] No saved models found — auto-training on synthetic data...")
        from utils.feature_engineering import prepare_training_data
        X, y = prepare_training_data(subject=cfg["decoding"]["physionet_subject"])
        
        # Train both paths
        decoder.train(X, y)
        decoder.save_models()

    # Start streaming
    bridge.start_stream()
    time.sleep(1.0)  # Let buffer fill

    # Calibrate safety monitor baseline
    init_window = bridge.get_window(n_samples)
    if init_window:
        monitor.calibrate_baseline(init_window["eeg"])

    # Adaptive learning buffer
    adaptive_X, adaptive_y = [], []
    last_adaptive_time = time.time()
    loop_count = 0

    print("[inference] Starting real-time loop... (Ctrl+C to stop)\n")

    try:
        while True:
            t_loop_start = time.perf_counter()

            # --- Stage 1: Input ---
            bench.start("input")
            window = bridge.get_window(n_samples)
            if window is None:
                time.sleep(0.01)
                continue
            eeg = window["eeg"]   # (n_samples, n_channels)
            imu = window["imu"]   # (n_samples, 4)
            bench.end("input")

            # --- Stage 2: Processing ---
            bench.start("processing")
            features = pipeline.process(eeg, imu)
            bench.end("processing")

            # --- Stage 3: Decoding ---
            bench.start("decoding")
            result = decoder.predict(features)
            bench.end("decoding")

            # --- Stage 4: Safety check ---
            bench.start("safety")
            safety_status = monitor.update(eeg)
            if safety_status["fatigue"]:
                print(f"[inference] ⚠ Fatigue detected — drift {safety_status['drift_pct']:.1f}%")
            bench.end("safety")

            # --- Stage 5: Transmission ---
            if monitor.is_safe:
                bench.start("transmission")
                tx_latency = sender.send_intent(result["intent"], result["confidence"])
                bench.end("transmission")
            else:
                print("[inference] Safety hold — no command sent")

            # --- Latency logging ---
            e2e_ms = (time.perf_counter() - t_loop_start) * 1000
            bench.record_e2e(e2e_ms)
            loop_count += 1

            # --- Adaptive learning ---
            if result["confidence"] > 0.85:
                adaptive_X.append(features)
                adaptive_y.append(result["intent"])

            if (time.time() - last_adaptive_time > adaptive_interval
                    and len(adaptive_X) >= 10):
                print(f"[inference] Self-healing update with {len(adaptive_X)} samples")
                decoder.incremental_update(
                    np.array(adaptive_X),
                    np.array(adaptive_y)
                )
                adaptive_X, adaptive_y = [], []
                last_adaptive_time = time.time()

            # --- Precise timing ---
            # Sleep only the remaining time of the step interval
            elapsed_s = time.perf_counter() - t_loop_start
            sleep_time = max(0, step_time_s - elapsed_s)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[inference] Stopped by user")
    finally:
        bridge.stop_stream()
        sender.disconnect()
        bench.print_report()
        print(f"[inference] Total loops: {loop_count}")


if __name__ == "__main__":
    run()
