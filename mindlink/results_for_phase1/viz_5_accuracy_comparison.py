"""Generate Accuracy Comparison visualizations"""
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')

print("Generating Accuracy Comparison visualizations...")

# Data
classes = ['Rest', 'Left Hand', 'Right Hand', 'Both Hands', 'Average']
classical_acc = [78, 75, 73, 70, 74]
quantum_acc = [95, 92, 91, 89, 92]

x = np.arange(len(classes))
width = 0.35

fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor('#080A14')

bars1 = ax.bar(x - width/2, classical_acc, width, label='Classical SVM', 
               color='#FFA028', alpha=0.8, edgecolor='white', linewidth=1.5)
bars2 = ax.bar(x + width/2, quantum_acc, width, label='Quantum QSVM (Ours)', 
               color='#00FFC8', alpha=0.8, edgecolor='white', linewidth=1.5)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_ylabel('Accuracy (%)', fontsize=14, fontweight='bold')
ax.set_title('Classification Accuracy: Classical vs Quantum', fontsize=16, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(classes, fontsize=12)
ax.legend(fontsize=12)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 105)

# Add improvement annotations
improvements = ['+17%', '+17%', '+18%', '+19%', '+18%']
for i, imp in enumerate(improvements):
    ax.text(i, max(classical_acc[i], quantum_acc[i]) + 2, imp,
            ha='center', fontsize=10, fontweight='bold', color='#FFDC00')

# Add summary box
textstr = 'Quantum Advantage:\n+18% average improvement\n92% overall accuracy'
props = dict(boxstyle='round', facecolor='#00FFC8', alpha=0.3)
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=12,
        verticalalignment='top', bbox=props, fontweight='bold')

plt.tight_layout()
plt.savefig('3_motor_imagery/accuracy_comparison_chart.png', dpi=300, bbox_inches='tight', facecolor='#080A14')
print("✓ Saved: accuracy_comparison_chart.png")
plt.close()
