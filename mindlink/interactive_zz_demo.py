"""
Interactive ZZ Feature Map Demo
================================
Step-by-step walkthrough of how EEG signals map to Hilbert space.
Run this to understand each component of the quantum encoding.
"""

import numpy as np
import matplotlib.pyplot as plt

try:
    from qiskit.circuit.library import ZZFeatureMap
    from qiskit.quantum_info import Statevector
    from qiskit.visualization import plot_bloch_multivector
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("Install Qiskit: pip install qiskit qiskit-aer")


def step1_show_eeg_features():
    """Step 1: Show what EEG features look like."""
    print("\n" + "="*70)
    print("STEP 1: EEG FEATURES (Classical Data)")
    print("="*70)
    print("""
After processing raw EEG signals, we extract features like:
- CSP (Common Spatial Patterns) components
- Power spectral density in mu band (8-13 Hz)
- Power spectral density in beta band (13-30 Hz)
- From motor cortex channels (C3, C4)

These features are NORMALIZED to [0, π] range for quantum encoding.
    """)
    
    # Example: Left hand motor imagery
    features = np.array([
        2.1,  # Feature 0: High C3 mu power (left motor cortex active)
        0.8,  # Feature 1: Low C4 mu power
        1.5,  # Feature 2: Moderate C3 beta power
        0.3,  # Feature 3: Low C4 beta power
        1.2,  # Feature 4: CSP component 1
        0.5,  # Feature 5: CSP component 2
        1.8,  # Feature 6: Additional PSD feature
        0.4   # Feature 7: Additional PSD feature
    ])
    
    print("Example: LEFT HAND motor imagery")
    print("-" * 70)
    for i, val in enumerate(features):
        bar = "█" * int(val * 10 / np.pi)
        print(f"  Feature {i}: {val:.3f} rad  {bar}")
    
    print(f"\nThese {len(features)} classical numbers will be encoded into")
    print(f"a quantum state in 2^{len(features)} = {2**len(features)}-dimensional Hilbert space!")
    
    return features


def step2_explain_hilbert_space():
    """Step 2: Explain Hilbert space."""
    print("\n" + "="*70)
    print("STEP 2: HILBERT SPACE (Where Quantum States Live)")
    print("="*70)
    print("""
WHAT IS HILBERT SPACE?
- A complex vector space where quantum states exist
- For n qubits: dimension = 2^n
- Each point is a quantum state |ψ⟩

For 8 qubits (our case):
- Dimension: 2^8 = 256
- Basis states: |00000000⟩, |00000001⟩, ..., |11111111⟩
- Any state: |ψ⟩ = α₀|00000000⟩ + α₁|00000001⟩ + ... + α₂₅₅|11111111⟩
- Constraint: Σ|αᵢ|² = 1 (normalization)

WHY USE IT FOR EEG?
- Classical features → quantum superposition
- Quantum interference can detect subtle patterns
- Entanglement captures feature correlations
- Quantum kernel methods can outperform classical ML
    """)


def step3_build_zz_feature_map():
    """Step 3: Build and explain ZZ feature map."""
    print("\n" + "="*70)
    print("STEP 3: ZZ FEATURE MAP (The Encoding Circuit)")
    print("="*70)
    print("""
The ZZ Feature Map has 3 layers per repetition:

LAYER 1: Hadamard Gates (Create Superposition)
  H|0⟩ = (|0⟩ + |1⟩)/√2
  Applied to all qubits → creates equal superposition

LAYER 2: RZ Rotations (Encode Features)
  RZ(φ)|ψ⟩ = e^(-iφZ/2)|ψ⟩
  Each qubit gets: RZ(xᵢ) where xᵢ is the i-th feature
  This encodes classical data as quantum phases

LAYER 3: ZZ Entanglement (Capture Correlations)
  ZZ(φ) = exp(-iφZ⊗Z/2)
  Applied between neighboring qubits: (q0,q1), (q1,q2), ..., (q6,q7)
  Angle: φ = (π - xᵢ)(π - xⱼ)
  Creates quantum correlations between features

REPETITIONS: Repeat layers 1-3 (reps=1 in config)
  → Encodes 8 EEG features into 256-dimensional Hilbert space
    """)
    
    if not QISKIT_AVAILABLE:
        print("\n⚠ Qiskit not available - cannot show circuit")
        return None
    
    # Build the circuit
    feature_map = ZZFeatureMap(feature_dimension=8, reps=1, entanglement='linear')
    
    print("\nCircuit Structure:")
    print("-" * 70)
    print(feature_map.decompose())
    
    return feature_map


def step4_encode_and_visualize(features, feature_map):
    """Step 4: Encode features and show resulting quantum state."""
    if not QISKIT_AVAILABLE:
        print("\n⚠ Qiskit required for encoding")
        return
    
    print("\n" + "="*70)
    print("STEP 4: ENCODING PROCESS (Classical → Quantum)")
    print("="*70)
    
    # Bind features to circuit
    circuit = feature_map.assign_parameters(features)
    
    # Get quantum state
    statevector = Statevector.from_instruction(circuit)
    
    print("\nINPUT (Classical):")
    print("-" * 70)
    print(f"  8 real numbers: {features}")
    
    print("\nOUTPUT (Quantum State in Hilbert Space):")
    print("-" * 70)
    print(f"  State vector |ψ⟩ with {len(statevector.data)} complex amplitudes")
    print(f"  Normalization check: Σ|αᵢ|² = {np.sum(np.abs(statevector.data)**2):.6f}")
    
    print("\n  Top 10 Amplitudes (showing first 10 of 256):")
    for i in range(min(10, len(statevector.data))):
        amp = statevector.data[i]
        basis = format(i, '08b')
        prob = np.abs(amp)**2
        bar = "█" * int(prob * 100)
        print(f"    |{basis}⟩: {amp.real:+.3f}{amp.imag:+.3f}i  P={prob:.4f}  {bar}")
    
    # Visualize
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # Plot 1: Input features
    axes[0].bar(range(8), features, color='steelblue', alpha=0.7, edgecolor='black')
    axes[0].axhline(np.pi, color='red', linestyle='--', alpha=0.5, label='π')
    axes[0].set_xlabel('Feature Index')
    axes[0].set_ylabel('Value (radians)')
    axes[0].set_title('Input: Classical EEG Features (8 features)')
    axes[0].legend()
    axes[0].grid(axis='y', alpha=0.3)
    
    # Plot 2: State amplitudes (show first 32 of 256)
    n_show = min(32, len(statevector.data))
    indices = np.arange(n_show)
    real_parts = statevector.data[:n_show].real
    imag_parts = statevector.data[:n_show].imag
    width = 0.35
    axes[1].bar(indices - width/2, real_parts, width, label='Real', alpha=0.7)
    axes[1].bar(indices + width/2, imag_parts, width, label='Imag', alpha=0.7)
    axes[1].set_xlabel('Basis State (first 32 of 256)')
    axes[1].set_ylabel('Amplitude')
    axes[1].set_title('Output: Quantum State Amplitudes')
    axes[1].legend()
    axes[1].grid(axis='y', alpha=0.3)
    
    # Plot 3: Probabilities (show first 32 of 256)
    probs = np.abs(statevector.data[:n_show])**2
    axes[2].bar(indices, probs, color='green', alpha=0.7, edgecolor='black')
    axes[2].set_xlabel('Basis State (first 32 of 256)')
    axes[2].set_ylabel('Probability |α|²')
    axes[2].set_title('Measurement Probabilities')
    axes[2].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('mindlink/zz_encoding_demo.png', dpi=150, bbox_inches='tight')
    print("\n✓ Visualization saved to: mindlink/zz_encoding_demo.png")
    plt.show()


def step5_compare_different_classes():
    """Step 5: Compare quantum states for different motor imagery classes."""
    if not QISKIT_AVAILABLE:
        print("\n⚠ Qiskit required")
        return
    
    print("\n" + "="*70)
    print("STEP 5: COMPARING DIFFERENT MOTOR IMAGERY CLASSES")
    print("="*70)
    print("""
Different motor imagery patterns → Different quantum states
The quantum kernel can measure similarity between states!
    """)
    
    feature_map = ZZFeatureMap(feature_dimension=8, reps=1, entanglement='linear')
    
    classes = {
        'Left Hand': np.array([2.1, 0.8, 1.5, 0.3, 1.2, 0.5, 1.8, 0.4]),
        'Right Hand': np.array([0.5, 2.3, 0.9, 1.8, 0.6, 2.1, 1.0, 1.9]),
        'Rest': np.array([0.2, 0.3, 0.1, 0.2, 0.3, 0.2, 0.1, 0.3]),
        'Both Hands': np.array([1.9, 1.8, 1.6, 1.7, 1.8, 1.9, 1.7, 1.6])
    }
    
    states = {}
    for name, features in classes.items():
        circuit = feature_map.assign_parameters(features)
        states[name] = Statevector.from_instruction(circuit)
        print(f"\n{name}:")
        print(f"  Features: {features}")
        print(f"  Top basis state: |{format(np.argmax(np.abs(states[name].data)**2), '08b')}⟩")
        print(f"  Max probability: {np.max(np.abs(states[name].data)**2):.4f}")
    
    # Compute quantum kernel (inner products)
    print("\n" + "-"*70)
    print("QUANTUM KERNEL MATRIX (State Similarities):")
    print("-"*70)
    print("K(i,j) = |⟨ψᵢ|ψⱼ⟩|² (overlap between quantum states)")
    print()
    
    names = list(classes.keys())
    print(f"{'':12}", end='')
    for name in names:
        print(f"{name:12}", end='')
    print()
    
    for i, name1 in enumerate(names):
        print(f"{name1:12}", end='')
        for j, name2 in enumerate(names):
            # Quantum kernel: |<ψ1|ψ2>|^2
            overlap = np.abs(np.vdot(states[name1].data, states[name2].data))**2
            print(f"{overlap:12.4f}", end='')
        print()
    
    print("\nInterpretation:")
    print("  • Diagonal = 1.0 (state with itself)")
    print("  • Off-diagonal < 1.0 (different states)")
    print("  • Lower values = more distinguishable classes")
    print("  • QSVM uses this kernel for classification!")


def main():
    """Run the complete interactive demo."""
    print("\n" + "="*70)
    print("INTERACTIVE ZZ FEATURE MAP DEMONSTRATION")
    print("How EEG Signals Map to Quantum Hilbert Space")
    print("="*70)
    
    # Step 1: Show EEG features
    features = step1_show_eeg_features()
    input("\nPress Enter to continue to Step 2...")
    
    # Step 2: Explain Hilbert space
    step2_explain_hilbert_space()
    input("\nPress Enter to continue to Step 3...")
    
    # Step 3: Build ZZ feature map
    feature_map = step3_build_zz_feature_map()
    input("\nPress Enter to continue to Step 4...")
    
    # Step 4: Encode and visualize
    if feature_map is not None:
        step4_encode_and_visualize(features, feature_map)
        input("\nPress Enter to continue to Step 5...")
        
        # Step 5: Compare classes
        step5_compare_different_classes()
    
    print("\n" + "="*70)
    print("DEMO COMPLETE!")
    print("="*70)
    print("""
KEY TAKEAWAYS:
1. EEG features (8 numbers) → Quantum state (256 complex amplitudes)
2. ZZ feature map creates superposition + entanglement
3. Different motor imagery → Different quantum states
4. Quantum kernel measures state similarity
5. QSVM uses this for classification

Next: Run train_models.py to train the quantum classifier!
    """)


if __name__ == "__main__":
    main()
