"""
Latency Benchmarking Utilities
Measures and logs end-to-end pipeline latency.
"""

import time
import numpy as np
from collections import deque


class LatencyBenchmark:
    """Tracks per-stage and end-to-end latency with percentile reporting."""

    def __init__(self, target_ms: float = 150.0, log_interval: int = 10):
        self.target_ms = target_ms
        self.log_interval = log_interval
        self._stages: dict[str, deque] = {}
        self._e2e: deque = deque(maxlen=1000)
        self._loop_count = 0
        self._timers: dict[str, float] = {}

    def start(self, stage: str):
        """Mark start of a pipeline stage."""
        self._timers[stage] = time.perf_counter()

    def end(self, stage: str) -> float:
        """Mark end of stage and record latency."""
        if stage not in self._timers:
            return 0.0
        elapsed_ms = (time.perf_counter() - self._timers[stage]) * 1000
        if stage not in self._stages:
            self._stages[stage] = deque(maxlen=1000)
        self._stages[stage].append(elapsed_ms)
        return elapsed_ms

    def record_e2e(self, latency_ms: float):
        """Record end-to-end latency for one full loop."""
        self._e2e.append(latency_ms)
        self._loop_count += 1
        if self._loop_count % self.log_interval == 0:
            self.print_report()

    def print_report(self):
        """Print latency statistics."""
        if not self._e2e:
            return
        arr = np.array(self._e2e)
        print("\n" + "="*50)
        print(f"[latency] Loop #{self._loop_count} — End-to-End Latency Report")
        print(f"  Mean:   {arr.mean():.1f} ms")
        print(f"  Median: {np.median(arr):.1f} ms")
        print(f"  P95:    {np.percentile(arr, 95):.1f} ms  (target ≤ {self.target_ms} ms)")
        print(f"  P99:    {np.percentile(arr, 99):.1f} ms")
        print(f"  Max:    {arr.max():.1f} ms")

        for stage, times in self._stages.items():
            t = np.array(times)
            print(f"  [{stage}] mean={t.mean():.1f} ms, p95={np.percentile(t, 95):.1f} ms")

        violations = np.sum(arr > self.target_ms)
        pct = violations / len(arr) * 100
        if pct > 5:
            print(f"  ⚠ {pct:.1f}% of loops exceeded {self.target_ms} ms target!")
        else:
            print(f"  ✓ {100-pct:.1f}% of loops within target")
        print("="*50 + "\n")

    def get_p95(self) -> float:
        if not self._e2e:
            return 0.0
        return float(np.percentile(self._e2e, 95))
