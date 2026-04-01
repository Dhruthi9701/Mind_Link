# Instructions to Copy Visualization Images

## Images Already Available in Project

The following images already exist in the `mindlink/` folder and should be copied to the appropriate results subfolders:

### Motor Imagery Simulations (for Section 3)
Copy these to `results_for_phase1/3_motor_imagery/`:

```bash
# From mindlink/ folder
cp zz_simulation_rest_state.png results_for_phase1/3_motor_imagery/
cp zz_simulation_left_hand_motor_imagery.png results_for_phase1/3_motor_imagery/
cp zz_simulation_right_hand_motor_imagery.png results_for_phase1/3_motor_imagery/
cp zz_simulation_both_hands_motor_imagery.png results_for_phase1/3_motor_imagery/
```

### ZZ Encoding Visualizations (for Section 2)
Copy these to `results_for_phase1/2_zz_encoding/`:

```bash
# From mindlink/ folder
cp zz_encoding_demo.png results_for_phase1/2_zz_encoding/
cp zz_feature_map_flow.png results_for_phase1/2_zz_encoding/
```

---

## Images to Generate

### Section 1: Signal Isolation
Run the quantum visualization and capture screenshots:

```bash
cd quantum_simulation
python quantum_3d_viz.py
# Press SPACE to go to Stage 1
# Take screenshot → save as: results_for_phase1/1_signal_isolation/eeg_signal_stage1.png
```

### Section 3: Motor Imagery (Additional)
Run the quantum visualization for all 4 patterns:

```bash
cd quantum_simulation
python quantum_3d_viz.py
# Press 1 for Left Hand → SPACE to Stage 5 → screenshot
# Press 2 for Right Hand → SPACE to Stage 5 → screenshot
# Press 3 for Rest → SPACE to Stage 5 → screenshot
# Press 4 for Both Hands → SPACE to Stage 5 → screenshot
```

Save as:
- `results_for_phase1/3_motor_imagery/quantum_kernel_matrix_left.png`
- `results_for_phase1/3_motor_imagery/quantum_kernel_matrix_right.png`
- `results_for_phase1/3_motor_imagery/quantum_kernel_matrix_rest.png`
- `results_for_phase1/3_motor_imagery/quantum_kernel_matrix_both.png`

### Section 4: Latency Metrics
Create a simple bar chart using Python:

```python
import matplotlib.pyplot as plt
import numpy as np

# Latency data
stages = ['Signal\nAcquisition', 'Signal\nProcessing', 'Feature\nExtraction', 
          'Quantum\nEncoding', 'Classification', 'Command\nGeneration', 'Transmission']
times = [10, 25, 10, 30, 15, 5, 5]
colors = ['#00B4FF', '#B480FF', '#00FFC8', '#FF64B4', '#50FF78', '#FFA028', '#FFDC00']

plt.figure(figsize=(12, 6))
plt.bar(stages, times, color=colors, edgecolor='white', linewidth=2)
plt.ylabel('Time (ms)', fontsize=14)
plt.title('Mind Link Pipeline Latency Breakdown', fontsize=16, fontweight='bold')
plt.axhline(y=100, color='red', linestyle='--', label='Total: 100 ms')
plt.axhline(y=150, color='orange', linestyle='--', label='Target: 150 ms')
plt.legend()
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('results_for_phase1/4_latency_metrics/latency_breakdown_chart.png', dpi=300, bbox_inches='tight')
plt.show()
```

### Section 5: Protocol Synthesis
Create MAVLink packet diagram:

```python
import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(14, 8))

# Packet structure
packet_fields = [
    ('STX', 1, '#FF6B6B'),
    ('LEN', 1, '#4ECDC4'),
    ('SEQ', 1, '#45B7D1'),
    ('SYS', 1, '#96CEB4'),
    ('COMP', 1, '#FFEAA7'),
    ('MSG_ID', 1, '#DFE6E9'),
    ('PAYLOAD', 12, '#74B9FF'),
    ('CRC', 2, '#A29BFE')
]

x_offset = 0
for field, width, color in packet_fields:
    rect = patches.Rectangle((x_offset, 0), width, 1, linewidth=2, 
                             edgecolor='black', facecolor=color)
    ax.add_patch(rect)
    ax.text(x_offset + width/2, 0.5, field, ha='center', va='center', 
           fontsize=10, fontweight='bold')
    x_offset += width

ax.set_xlim(0, x_offset)
ax.set_ylim(0, 1)
ax.axis('off')
ax.set_title('MAVLink RC_CHANNELS_OVERRIDE Packet Structure', 
            fontsize=16, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig('results_for_phase1/5_protocol_synthesis/mavlink_packet_structure.png', 
           dpi=300, bbox_inches='tight')
plt.show()
```

---

## Quick Copy Commands (Windows PowerShell)

```powershell
# Navigate to project root
cd E:\Mind_Link\mindlink

# Copy motor imagery simulations
Copy-Item "zz_simulation_rest_state.png" "results_for_phase1\3_motor_imagery\"
Copy-Item "zz_simulation_left_hand_motor_imagery.png" "results_for_phase1\3_motor_imagery\"
Copy-Item "zz_simulation_right_hand_motor_imagery.png" "results_for_phase1\3_motor_imagery\"
Copy-Item "zz_simulation_both_hands_motor_imagery.png" "results_for_phase1\3_motor_imagery\"

# Copy ZZ encoding visualizations
Copy-Item "zz_encoding_demo.png" "results_for_phase1\2_zz_encoding\"
Copy-Item "zz_feature_map_flow.png" "results_for_phase1\2_zz_encoding\"
```

---

## Folder Structure After Copying

```
results_for_phase1/
├── README.md
├── COPY_IMAGES_INSTRUCTIONS.md
├── 1_signal_isolation/
│   ├── SIGNAL_ISOLATION_RESULTS.md
│   └── eeg_signal_stage1.png (to be captured)
├── 2_zz_encoding/
│   ├── ZZ_ENCODING_RESULTS.md
│   ├── zz_encoding_demo.png (copy from mindlink/)
│   └── zz_feature_map_flow.png (copy from mindlink/)
├── 3_motor_imagery/
│   ├── MOTOR_IMAGERY_DIFFERENTIATION.md
│   ├── zz_simulation_rest_state.png (copy from mindlink/)
│   ├── zz_simulation_left_hand_motor_imagery.png (copy from mindlink/)
│   ├── zz_simulation_right_hand_motor_imagery.png (copy from mindlink/)
│   └── zz_simulation_both_hands_motor_imagery.png (copy from mindlink/)
├── 4_latency_metrics/
│   ├── LATENCY_BENCHMARKING.md
│   └── latency_breakdown_chart.png (to be generated)
├── 5_protocol_synthesis/
│   ├── NEURAL_KINETIC_PROTOCOL.md
│   └── mavlink_packet_structure.png (to be generated)
└── presentation_slides/
    └── PRESENTATION_SUMMARY.md
```

---

## Verification Checklist

After copying/generating all images, verify:

- [ ] All 4 motor imagery simulations in Section 3
- [ ] Both ZZ encoding visualizations in Section 2
- [ ] Latency breakdown chart in Section 4
- [ ] MAVLink packet diagram in Section 5
- [ ] All markdown files are readable
- [ ] All images display correctly

---

**Note**: The existing PNG files in the mindlink/ folder are already high-quality and ready for presentation use.
