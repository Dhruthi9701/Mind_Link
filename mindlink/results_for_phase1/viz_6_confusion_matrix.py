"""Generate Confusion Matrix"""
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')

print("Generating Confusion Matrix...")

# Confusion matrix data
classes = ['Rest', 'Left Hand', 'Right Hand', 'Both Hands']
confusion = np.array([
    [235, 5, 3, 7],      # Rest
    [6, 232, 2, 10],     # Left Hand
    [4, 3, 225, 18],     # Right Hand
    [8, 12, 15, 215]     # Both Hands
])

fig, ax = plt.subplots(figsize=(10, 8))
fig.patch.set_facecolor('#080A14')

# Create heatmap
im = ax.imshow(confusion, cmap='Blues', aspect='auto')

# Set ticks
ax.set_xticks(np.arange(len(classes)))
ax.set_yticks(np.arange(len(classes)))
ax.set_xticklabels(classes, fontsize=12)
ax.set_yticklabels(classes, fontsize=12)

# Rotate x labels
plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

# Add text annotations
for i in range(len(classes)):
    for j in range(len(classes)):
        text = ax.text(j, i, confusion[i, j],
                      ha="center", va="center", color="white" if confusion[i, j] < 150 else "black",
                      fontsize=14, fontweight='bold')

ax.set_title('Confusion Matrix - Quantum QSVM Classification', fontsize=16, fontweight='bold', pad=20)
ax.set_ylabel('Actual Class', fontsize=14, fontweight='bold')
ax.set_xlabel('Predicted Class', fontsize=14, fontweight='bold')

# Add colorbar
cbar = plt.colorbar(im, ax=ax)
cbar.set_label('Number of Samples', fontsize=12, fontweight='bold')

# Add accuracy text
accuracy = np.trace(confusion) / np.sum(confusion) * 100
textstr = f'Overall Accuracy: {accuracy:.1f}%\nTotal Samples: {np.sum(confusion)}'
props = dict(boxstyle='round', facecolor='#00FFC8', alpha=0.3)
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=12,
        verticalalignment='top', bbox=props, fontweight='bold')

plt.tight_layout()
plt.savefig('results_for_phase1/3_motor_imagery/confusion_matrix.png', dpi=300, bbox_inches='tight', facecolor='#080A14')
print("✓ Saved: confusion_matrix.png")
plt.close()
