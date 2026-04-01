# Visualization Generation Instructions

## Quick Start

### Option 1: Run All Visualizations (Recommended)
```bash
cd E:\Mind_Link\mindlink
python results_for_phase1/run_all_visualizations.py
```

This will generate all 8 visualization files automatically.

---

### Option 2: Run Individual Scripts
```bash
cd E:\Mind_Link\mindlink\results_for_phase1

# Signal Isolation
python viz_1_signal_isolation.py
python viz_2_frequency_spectrum.py

# Latency Metrics
python viz_3_latency_breakdown.py
python viz_4_cloud_vs_edge.py

# Motor Imagery Classification
python viz_5_accuracy_comparison.py
python viz_6_confusion_matrix.py
python viz_7_quantum_kernel_matrix.py

# Protocol Synthesis
python viz_8_mavlink_packet.py
```

---

## Generated Visualizations

### 1. Signal Isolation (2 files)
- `1_signal_isolation/before_after_comparison.png`
  - Before: Raw noisy EEG signal
  - After: Clean Mu-rhythm (8-13 Hz)
  - Shows 4-5x SNR improvement

- `1_signal_isolation/frequency_spectrum_comparison.png`
  - Frequency domain analysis
  - Shows Mu-band isolation
  - Power line noise removal

---

### 2. Motor Imagery Classification (3 files)
- `3_motor_imagery/accuracy_comparison_chart.png`
  - Classical SVM vs Quantum QSVM
  - Shows +18% improvement
  - Per-class accuracy breakdown

- `3_motor_imagery/confusion_matrix.png`
  - 4x4 confusion matrix
  - 1000 total samples
  - 92% overall accuracy

- `3_motor_imagery/quantum_kernel_matrix.png`
  - Quantum state similarity
  - Shows distinguishability
  - Kernel values K(x,x')

---

### 3. Latency Metrics (2 files)
- `4_latency_metrics/latency_breakdown_chart.png`
  - 7-stage pipeline breakdown
  - 100 ms total latency
  - Color-coded by stage

- `4_latency_metrics/cloud_vs_edge_comparison.png`
  - Cloud: 535 ms
  - Edge: 85 ms
  - 6.3x faster!

---

### 4. Protocol Synthesis (1 file)
- `5_protocol_synthesis/mavlink_packet_structure.png`
  - MAVLink packet format
  - RC_CHANNELS_OVERRIDE (ID: 70)
  - 20-byte packet structure

---

## Requirements

### Python Packages
```bash
pip install matplotlib numpy scipy seaborn
```

Or if you already have the environment:
```bash
conda activate mind_link
# Packages should already be installed
```

---

## Verification Checklist

After running the scripts, verify:

- [ ] `1_signal_isolation/before_after_comparison.png` exists
- [ ] `1_signal_isolation/frequency_spectrum_comparison.png` exists
- [ ] `3_motor_imagery/accuracy_comparison_chart.png` exists
- [ ] `3_motor_imagery/confusion_matrix.png` exists
- [ ] `3_motor_imagery/quantum_kernel_matrix.png` exists
- [ ] `4_latency_metrics/latency_breakdown_chart.png` exists
- [ ] `4_latency_metrics/cloud_vs_edge_comparison.png` exists
- [ ] `5_protocol_synthesis/mavlink_packet_structure.png` exists

**Total: 8 visualization files**

---

## Copy Existing Simulation Images

Don't forget to also copy the quantum simulation images:

```bash
cd E:\Mind_Link\mindlink

# Copy motor imagery simulations
copy zz_simulation_rest_state.png results_for_phase1\3_motor_imagery\
copy zz_simulation_left_hand_motor_imagery.png results_for_phase1\3_motor_imagery\
copy zz_simulation_right_hand_motor_imagery.png results_for_phase1\3_motor_imagery\
copy zz_simulation_both_hands_motor_imagery.png results_for_phase1\3_motor_imagery\

# Copy ZZ encoding visualizations
copy zz_encoding_demo.png results_for_phase1\2_zz_encoding\
copy zz_feature_map_flow.png results_for_phase1\2_zz_encoding\
```

---

## Troubleshooting

### Error: "No module named 'matplotlib'"
```bash
conda activate mind_link
pip install matplotlib numpy scipy seaborn
```

### Error: "Permission denied"
- Close any image viewers
- Run as administrator if needed

### Error: "File not found"
- Make sure you're in the correct directory
- Check that all .py files exist

---

## Output Quality

All images are generated with:
- **Resolution**: 300 DPI (publication quality)
- **Format**: PNG with transparency
- **Style**: Dark background (matches presentation theme)
- **Size**: Optimized for slides (14-16 inches wide)

---

## Next Steps

After generating visualizations:

1. Review all images
2. Copy to presentation slides
3. Use in results documentation
4. Include in technical reports

---

**Ready to generate? Run:**
```bash
python results_for_phase1/run_all_visualizations.py
```
