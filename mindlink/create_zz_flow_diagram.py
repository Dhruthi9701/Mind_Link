"""
Create a visual flow diagram showing EEG → Hilbert Space mapping.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def create_flow_diagram():
    """Create comprehensive flow diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Title
    ax.text(5, 11.5, 'EEG to Hilbert Space: ZZ Feature Map Pipeline',
            ha='center', va='top', fontsize=16, fontweight='bold')
    
    # Colors
    color_input = '#E8F4F8'
    color_process = '#FFF4E6'
    color_quantum = '#F0E6FF'
    color_output = '#E8F8E8'
    
    # 1. Raw EEG Input
    box1 = FancyBboxPatch((0.5, 9.5), 2, 1, boxstyle="round,pad=0.1",
                          facecolor=color_input, edgecolor='black', linewidth=2)
    ax.add_patch(box1)
    ax.text(1.5, 10.2, 'Raw EEG Signal', ha='center', va='center',
            fontsize=11, fontweight='bold')
    ax.text(1.5, 9.8, 'Motor Cortex\n(C3, C4)', ha='center', va='center',
            fontsize=9)
    
    # Arrow 1
    arrow1 = FancyArrowPatch((2.5, 10), (3.5, 10),
                            arrowstyle='->', mutation_scale=20, linewidth=2,
                            color='black')
    ax.add_patch(arrow1)
    ax.text(3, 10.3, 'Preprocessing', ha='center', fontsize=8, style='italic')
    
    # 2. Feature Extraction
    box2 = FancyBboxPatch((3.5, 9.5), 2, 1, boxstyle="round,pad=0.1",
                          facecolor=color_process, edgecolor='black', linewidth=2)
    ax.add_patch(box2)
    ax.text(4.5, 10.2, 'Feature Extraction', ha='center', va='center',
            fontsize=11, fontweight='bold')
    ax.text(4.5, 9.8, 'CSP + PSD\n(mu/beta bands)', ha='center', va='center',
            fontsize=9)
    
    # Arrow 2
    arrow2 = FancyArrowPatch((5.5, 10), (6.5, 10),
                            arrowstyle='->', mutation_scale=20, linewidth=2,
                            color='black')
    ax.add_patch(arrow2)
    ax.text(6, 10.3, 'Normalize', ha='center', fontsize=8, style='italic')
    
    # 3. Classical Features
    box3 = FancyBboxPatch((6.5, 9.5), 2, 1, boxstyle="round,pad=0.1",
                          facecolor=color_input, edgecolor='black', linewidth=2)
    ax.add_patch(box3)
    ax.text(7.5, 10.2, 'Classical Features', ha='center', va='center',
            fontsize=11, fontweight='bold')
    ax.text(7.5, 9.8, '4 values ∈ [0, π]', ha='center', va='center',
            fontsize=9)
    
    # Example features
    ax.text(7.5, 9.2, 'x = [2.1, 0.8, 1.5, 0.3]', ha='center', va='center',
            fontsize=8, family='monospace', style='italic')
    
    # Arrow down to quantum encoding
    arrow3 = FancyArrowPatch((7.5, 9.5), (7.5, 8.5),
                            arrowstyle='->', mutation_scale=20, linewidth=2,
                            color='black')
    ax.add_patch(arrow3)
    ax.text(7.8, 9, 'Quantum\nEncoding', ha='left', fontsize=8, style='italic')
    
    # 4. ZZ Feature Map (large box)
    box4 = FancyBboxPatch((3, 5.5), 6, 2.8, boxstyle="round,pad=0.1",
                          facecolor=color_quantum, edgecolor='purple', linewidth=3)
    ax.add_patch(box4)
    ax.text(6, 8.1, 'ZZ Feature Map Circuit', ha='center', va='center',
            fontsize=12, fontweight='bold', color='purple')
    
    # ZZ Feature Map components
    # Layer 1: Hadamard
    y_start = 7.5
    box_h = FancyBboxPatch((3.5, y_start), 1.5, 0.5, boxstyle="round,pad=0.05",
                           facecolor='lightblue', edgecolor='blue', linewidth=1)
    ax.add_patch(box_h)
    ax.text(4.25, y_start+0.25, 'H Gates', ha='center', va='center', fontsize=9)
    ax.text(4.25, y_start-0.3, 'Superposition', ha='center', va='center',
            fontsize=7, style='italic')
    
    # Arrow
    ax.arrow(5.1, y_start+0.25, 0.3, 0, head_width=0.1, head_length=0.1,
             fc='black', ec='black')
    
    # Layer 2: RZ
    box_rz = FancyBboxPatch((5.5, y_start), 1.5, 0.5, boxstyle="round,pad=0.05",
                            facecolor='lightgreen', edgecolor='green', linewidth=1)
    ax.add_patch(box_rz)
    ax.text(6.25, y_start+0.25, 'RZ(xᵢ)', ha='center', va='center', fontsize=9)
    ax.text(6.25, y_start-0.3, 'Encode Features', ha='center', va='center',
            fontsize=7, style='italic')
    
    # Arrow
    ax.arrow(7.1, y_start+0.25, 0.3, 0, head_width=0.1, head_length=0.1,
             fc='black', ec='black')
    
    # Layer 3: ZZ
    box_zz = FancyBboxPatch((7.5, y_start), 1.5, 0.5, boxstyle="round,pad=0.05",
                            facecolor='lightyellow', edgecolor='orange', linewidth=1)
    ax.add_patch(box_zz)
    ax.text(8.25, y_start+0.25, 'ZZ Gates', ha='center', va='center', fontsize=9)
    ax.text(8.25, y_start-0.3, 'Entanglement', ha='center', va='center',
            fontsize=7, style='italic')
    
    # Repetition indicator
    ax.annotate('', xy=(3.5, y_start-0.7), xytext=(9, y_start-0.7),
                arrowprops=dict(arrowstyle='<->', color='purple', lw=2))
    ax.text(6.25, y_start-1, 'Repeat 2×', ha='center', va='center',
            fontsize=9, color='purple', fontweight='bold')
    
    # Circuit depth info
    ax.text(6, 5.8, 'Circuit Depth ≤ 30 | Linear Entanglement',
            ha='center', va='center', fontsize=8, style='italic')
    
    # Arrow down to Hilbert space
    arrow4 = FancyArrowPatch((6, 5.5), (6, 4.5),
                            arrowstyle='->', mutation_scale=20, linewidth=2,
                            color='black')
    ax.add_patch(arrow4)
    
    # 5. Hilbert Space
    box5 = FancyBboxPatch((3.5, 2.5), 5, 1.8, boxstyle="round,pad=0.1",
                          facecolor=color_quantum, edgecolor='purple', linewidth=3)
    ax.add_patch(box5)
    ax.text(6, 4.1, 'Quantum State in Hilbert Space', ha='center', va='center',
            fontsize=12, fontweight='bold', color='purple')
    
    # State vector representation
    ax.text(6, 3.6, '|ψ⟩ = α₀|0000⟩ + α₁|0001⟩ + ... + α₁₅|1111⟩',
            ha='center', va='center', fontsize=9, family='monospace')
    ax.text(6, 3.2, 'Dimension: 2⁴ = 16', ha='center', va='center',
            fontsize=9, style='italic')
    ax.text(6, 2.9, 'Complex amplitudes: αᵢ ∈ ℂ', ha='center', va='center',
            fontsize=9, style='italic')
    ax.text(6, 2.6, 'Constraint: Σ|αᵢ|² = 1', ha='center', va='center',
            fontsize=9, style='italic')
    
    # Arrow down to kernel
    arrow5 = FancyArrowPatch((6, 2.5), (6, 1.5),
                            arrowstyle='->', mutation_scale=20, linewidth=2,
                            color='black')
    ax.add_patch(arrow5)
    ax.text(6.3, 2, 'Quantum\nKernel', ha='left', fontsize=8, style='italic')
    
    # 6. Classification
    box6 = FancyBboxPatch((4, 0.5), 4, 0.8, boxstyle="round,pad=0.1",
                          facecolor=color_output, edgecolor='green', linewidth=2)
    ax.add_patch(box6)
    ax.text(6, 1.1, 'QSVM Classification', ha='center', va='center',
            fontsize=11, fontweight='bold')
    ax.text(6, 0.7, 'Left | Right | Rest | Both', ha='center', va='center',
            fontsize=9)
    
    # Side panel: Key concepts
    side_x = 0.2
    ax.text(side_x, 7.5, 'KEY CONCEPTS', fontsize=10, fontweight='bold')
    
    concepts = [
        ('Hilbert Space', 'Complex vector space\nfor quantum states'),
        ('Superposition', '|ψ⟩ = α|0⟩ + β|1⟩\nMultiple states at once'),
        ('Entanglement', 'Quantum correlations\nbetween qubits'),
        ('Quantum Kernel', 'K(x,x\') = |⟨ψ(x)|ψ(x\')⟩|²\nState similarity')
    ]
    
    y_pos = 7
    for title, desc in concepts:
        ax.text(side_x, y_pos, f'• {title}:', fontsize=8, fontweight='bold')
        ax.text(side_x+0.1, y_pos-0.3, desc, fontsize=7, style='italic')
        y_pos -= 0.8
    
    # Bottom: Advantages
    ax.text(5, 0.1, 'Why Quantum? Exponential Hilbert space | Natural entanglement | Quantum interference patterns',
            ha='center', va='center', fontsize=8, style='italic',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('mindlink/zz_feature_map_flow.png', dpi=300, bbox_inches='tight',
                facecolor='white')
    print("✓ Flow diagram saved to: mindlink/zz_feature_map_flow.png")
    plt.show()


if __name__ == "__main__":
    print("\nCreating ZZ Feature Map flow diagram...")
    create_flow_diagram()
    print("Done!\n")
