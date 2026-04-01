"""Generate Latency Breakdown visualizations"""
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')

print("Generating Latency Breakdown visualizations...")

# Latency data
stages = ['Signal\nAcquisition', 'Signal\nProcessing', 'Feature\nExtraction', 
          'Quantum\nEncoding', 'Classification', 'Command\nGeneration', 'Transmission']
times = [10, 25, 10, 30, 15, 5, 5]
colors = ['#00B4FF', '#B480FF', '#00FFC8', '#FF64B4', '#50FF78', '#FFA028', '#FFDC00']

fig, ax = plt.subplots(figsize=(14, 8))
fig.patch.set_facecolor('#080A14')

bars = ax.bar(stages, times, color=colors, edgecolor='white', linewidth=2, alpha=0.9)

# Add value labels on bars
for bar, time in zip(bars, times):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{time} ms\n({time}%)',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_ylabel('Time (ms)', fontsize=14, fontweight='bold')
ax.set_title('Mind Link Pipeline Latency Breakdown', fontsize=16, fontweight='bold', pad=20)
ax.axhline(y=100, color='#00FFC8', linestyle='--', linewidth=2, label='Total: 100 ms ✓')
ax.axhline(y=150, color='#FFA028', linestyle='--', linewidth=2, label='Target: 150 ms')
ax.legend(fontsize=12, loc='upper right')
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 160)

# Add text box
textstr = 'Total Latency: 100 ms\n33% faster than target\n99.8% reliability'
props = dict(boxstyle='round', facecolor='#00FFC8', alpha=0.3)
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=12,
        verticalalignment='top', bbox=props, fontweight='bold')

plt.tight_layout()
plt.savefig('4_latency_metrics/latency_breakdown_chart.png', dpi=300, bbox_inches='tight', facecolor='#080A14')
print("✓ Saved: latency_breakdown_chart.png")
plt.close()
