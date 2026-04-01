"""
Master script to generate all Phase 1 visualizations
Run this to create all charts and graphs for the presentation
"""

import os
import sys

print("=" * 70)
print("MIND LINK PHASE 1 - VISUALIZATION GENERATOR")
print("=" * 70)
print()

# Change to results folder
os.chdir('results_for_phase1')

# List of visualization scripts
scripts = [
    'viz_1_signal_isolation.py',
    'viz_2_frequency_spectrum.py',
    'viz_3_latency_breakdown.py',
    'viz_4_cloud_vs_edge.py',
    'viz_5_accuracy_comparison.py',
    'viz_6_confusion_matrix.py',
    'viz_7_quantum_kernel_matrix.py',
    'viz_8_mavlink_packet.py'
]

print(f"Running {len(scripts)} visualization scripts...\n")

for i, script in enumerate(scripts, 1):
    print(f"[{i}/{len(scripts)}] Running {script}...")
    try:
        exec(open(script).read())
        print(f"    ✓ Success\n")
    except Exception as e:
        print(f"    ✗ Error: {e}\n")

print("=" * 70)
print("VISUALIZATION GENERATION COMPLETE!")
print("=" * 70)
print("\nGenerated files:")
print("  1_signal_isolation/")
print("    - before_after_comparison.png")
print("    - frequency_spectrum_comparison.png")
print("  3_motor_imagery/")
print("    - accuracy_comparison_chart.png")
print("    - confusion_matrix.png")
print("    - quantum_kernel_matrix.png")
print("  4_latency_metrics/")
print("    - latency_breakdown_chart.png")
print("    - cloud_vs_edge_comparison.png")
print("  5_protocol_synthesis/")
print("    - mavlink_packet_structure.png")
print("\nAll visualizations ready for presentation!")
