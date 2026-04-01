"""Generate Cloud vs Edge comparison"""
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')

print("Generating Cloud vs Edge comparison...")

# Data
categories = ['Signal\nProcessing', 'Feature\nExtraction', 'Network\nUpload', 
              'Queue\nWait', 'Quantum\nEncoding', 'Classification', 
              'Network\nDownload', 'Command\nGen']

cloud_times = [25, 10, 75, 300, 30, 15, 75, 5]  # Total: 535 ms
edge_times = [25, 10, 0, 0, 30, 15, 0, 5]  # Total: 85 ms (without acquisition/transmission)

x = np.arange(len(categories))
width = 0.35

fig, ax = plt.subplots(figsize=(14, 8))
fig.patch.set_facecolor('#080A14')

bars1 = ax.bar(x - width/2, cloud_times, width, label='Cloud Quantum', 
               color='#FF6B6B', alpha=0.8, edgecolor='white', linewidth=1.5)
bars2 = ax.bar(x + width/2, edge_times, width, label='Edge Quantum (Ours)', 
               color='#00FFC8', alpha=0.8, edgecolor='white', linewidth=1.5)

ax.set_ylabel('Time (ms)', fontsize=14, fontweight='bold')
ax.set_title('Cloud vs Edge Quantum Computing Latency', fontsize=16, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.legend(fontsize=12)
ax.grid(axis='y', alpha=0.3)

# Add total time annotations
ax.text(0.15, 0.95, 'Cloud Total: 535 ms', transform=ax.transAxes, 
        fontsize=13, fontweight='bold', color='#FF6B6B',
        bbox=dict(boxstyle='round', facecolor='#FF6B6B', alpha=0.3))
ax.text(0.15, 0.88, 'Edge Total: 85 ms', transform=ax.transAxes, 
        fontsize=13, fontweight='bold', color='#00FFC8',
        bbox=dict(boxstyle='round', facecolor='#00FFC8', alpha=0.3))
ax.text(0.15, 0.81, '6.3x Faster!', transform=ax.transAxes, 
        fontsize=14, fontweight='bold', color='#FFDC00',
        bbox=dict(boxstyle='round', facecolor='#FFDC00', alpha=0.3))

plt.tight_layout()
plt.savefig('4_latency_metrics/cloud_vs_edge_comparison.png', dpi=300, bbox_inches='tight', facecolor='#080A14')
print("✓ Saved: cloud_vs_edge_comparison.png")
plt.close()
