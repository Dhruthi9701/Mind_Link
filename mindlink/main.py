"""
Mind Link — Main Orchestrator
Runs the complete 5-unit pipeline end-to-end.
Usage:
    python main.py                  # real-time inference (sim mode)
    python main.py --train          # train models first
    python main.py --checklist      # run pre-flight checklist
    python main.py --benchmark      # latency benchmark only
"""

from pathlib import Path
import sys
import yaml


def load_config():
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def main():
    args = sys.argv[1:]
    cfg = load_config()

    if "--checklist" in args:
        from pre_flight_checklist import run_checklist
        ok, _ = run_checklist()
        if not ok:
            print("Pre-flight failed. Aborting.")
            sys.exit(1)

    if "--train" in args:
        from train_models import train
        subject = cfg["decoding"]["physionet_subject"]
        train(subject=subject)

    if "--benchmark" in args:
        _run_benchmark(cfg)
        return

    # Default: real-time inference
    from real_time_inference import run
    run()


def _run_benchmark(cfg):
    """Quick latency benchmark without hardware."""
    import time
    import numpy as np
    from processing.denoising_pipeline import DenoisingPipeline
    from decoding.hybrid_decoder import HybridDecoder
    from utils.latency_benchmark import LatencyBenchmark

    print("\n[benchmark] Running 50-loop latency benchmark...")
    pipeline = DenoisingPipeline(config=cfg)
    decoder = HybridDecoder(config=cfg)
    decoder.load_models()
    bench = LatencyBenchmark(target_ms=cfg["latency"]["target_e2e_ms"], log_interval=50)

    fs = cfg["input"]["sample_rate"]
    n_samples = int(fs * cfg["processing"]["window_size_ms"] / 1000)
    n_channels = cfg["input"]["n_channels"]

    for i in range(50):
        t0 = time.perf_counter()
        eeg = np.random.randn(n_samples, n_channels) * 10.0
        imu = np.tile([1, 0, 0, 0], (n_samples, 1)).astype(float)
        features = pipeline.process(eeg, imu)
        result = decoder.predict(features)
        e2e = (time.perf_counter() - t0) * 1000
        bench.record_e2e(e2e)

    bench.print_report()


if __name__ == "__main__":
    main()
