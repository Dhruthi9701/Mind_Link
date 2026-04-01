"""Generate Quantum Kernel Matrix"""
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')

print("Generating Quantum Kernel Matrix...")

# Kernel matrix data (from simulation)
classes = ['Left', 'Right', 'Rest', 'Both']
kernel = np.array([
    [1.00, 0.12, 0.22, 0.63],  # Left
    [0.12, 1.00, 0.33, 0.53],  # Right
    [0.22, 0.33, 1.00, 0.34],  # Rest
    [0.63, 0.53, 0.34, 1.00]   # Both
])

fig, ax = plt.subplots(figsize=(10, 8))
fig.patch.set_facecolor('#080A14')

# Create heatmap
im = ax.imshow(kernel, cmap='viridis', aspect='auto', vmin=0, vmax=1)

# Set ticks
ax.set_xticks(np.arange(len(classes)))
ax.set_yticks(np.arange(len(classes)))
ax.set_xticklabels(classes, fontsize=13, fontweight='bold')
ax.set_yticklabels(classes, fontsize=13, fontweight='bold')

# Add text annotations
for i in range(len(classes)):
    for j in range(len(classes)):
        text = ax.text(j, i, f'{kernel[i, j]:.2f}',
                      ha="center", va="center", color="white",
                      fontsize=16, fontweight='bold')

ax.set_title('Quantum Kernel Matrix K(x,x\') = |⟨ψ(x)|ψ(x\')⟩|²', 
             fontsize=16, fontweight='bold', pad=20)
ax.set_ylabel('Pattern x', fontsize=14, fontweight='bold')
ax.set_xlabel('Pattern x\'', fontsize=14, fontweight='bold')

# Add colorbar
cbar = plt.colorbar(im, ax=ax)
cbar.set_label('Similarity', fontsize=12, fontweight='bold')

# Add interpretation text
textstr = 'Diagonal = 1.0 (identical)\nLow values = distinguishable\nHigh values = similar'
props = dict(boxstyle='round', facecolor='#00FFC8', alpha=0.3)
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=11,
        verticalalignment='top', bbox=props, fontweight='bold')

plt.tight_layout()
plt.savefig('3_motor_imagery/quantum_kernel_matrix.png', dpi=300, bbox_inches='tight', facecolor='#080A14')
print("✓ Saved: quantum_kernel_matrix.png")
plt.close()
