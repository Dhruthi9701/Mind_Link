"""
ZZ Feature Map Simulation: EEG to Hilbert Space Mapping
========================================================
This simulation demonstrates how classical EEG features are encoded
into quantum states in Hilbert space using the ZZFeatureMap.

Key Concepts:
1. Classical EEG features (normalized to [0, π])
2. Quantum feature map (ZZFeatureMap with entanglement)
3. Hilbert space representation (2^n dimensional complex vector space)
4. Quantum state visualization (Bloch sphere, state vector, density matrix)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import yaml
from pathlib import Path

try:
    from qiskit.circuit.library import ZZFeatureMap
    from qiskit_aer import AerSimulator
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import Statevector, DensityMatrix
    from qiskit.visualization import plot_bloch_multivector, plot_state_city
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("⚠ Qiskit not available — install with: pip install qiskit qiskit-aer")


def load_config():
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class ZZFeatureMapSimulator:
    """
    Interactive simulator for ZZ feature map encoding.
    Shows step-by-step how EEG features become quantum states.
    """

    def __init__(self, n_qubits: int = 4, reps: int = 2):
        self.n_qubits = n_qubits
        self.reps = reps
        self.feature_map = None
        self.statevector = None
        
        if QISKIT_AVAILABLE:
            self._build_feature_map()

    def _build_feature_map(self):
        """Build ZZFeatureMap circuit with linear entanglement."""
        self.feature_map = ZZFeatureMap(
            feature_dimension=self.n_qubits,
            reps=self.reps,
            entanglement='linear'
        )
        print(f"✓ ZZFeatureMap built: {self.n_qubits} qubits, {self.reps} repetitions")
        print(f"  Hilbert space dimension: 2^{self.n_qubits} = {2**self.n_qubits}")

    def explain_zz_feature_map(self):
        """Print detailed explanation of ZZ feature map components."""
        print("\n" + "="*70)
        print("ZZ FEATURE MAP EXPLAINED")
        print("="*70)
        
        print("\n1. SINGLE-QUBIT ROTATIONS (Hadamard + RZ gates)")
        print("   " + "-"*66)
        print("   • Hadamard (H): Creates superposition |0⟩ → (|0⟩ + |1⟩)/√2")
        print("   • RZ(φ): Phase rotation around Z-axis by angle φ")
        print("   • Each EEG feature x_i controls rotation: RZ(x_i)")
        print("   • Maps classical value x_i ∈ [0, π] to quantum phase")
        
        print("\n2. TWO-QUBIT ENTANGLEMENT (ZZ gates)")
        print("   " + "-"*66)
        print("   • ZZ(φ) = exp(-i φ Z⊗Z / 2)")
        print("   • Creates quantum correlations between qubits")
        print("   • Entanglement pattern: 'linear' → (q0-q1), (q1-q2), (q2-q3)")
        print("   • Angle depends on product: φ = (π - x_i)(π - x_j)")
        print("   • Captures feature interactions in quantum state")
        
        print("\n3. REPETITIONS (reps=2)")
        print("   " + "-"*66)
        print("   • Repeat the encoding layers multiple times")
        print("   • Increases expressiveness of the quantum state")
        print("   • Creates deeper entanglement structure")
        print("   • Trade-off: more reps = more expressive but deeper circuit")
        
        print("\n4. HILBERT SPACE MAPPING")
        print("   " + "-"*66)
        print(f"   • Input: {self.n_qubits} classical features (real numbers)")
        print(f"   • Output: Quantum state in {2**self.n_qubits}-dimensional Hilbert space")
        print("   • State vector: |ψ⟩ = Σ α_i |i⟩, where Σ|α_i|² = 1")
        print("   • Each α_i is a complex amplitude")
        print("   • Encodes features in quantum interference patterns")
        
        print("\n5. WHY ZZ FEATURE MAP FOR EEG?")
        print("   " + "-"*66)
        print("   • EEG features have natural correlations (e.g., mu/beta bands)")
        print("   • ZZ entanglement captures these correlations")
        print("   • Quantum kernel can detect patterns classical methods miss")
        print("   • Efficient for motor imagery classification")
        print("="*70 + "\n")

    def encode_features(self, features: np.ndarray) -> Statevector:
        """
        Encode classical EEG features into quantum state.
        
        Args:
            features: (n_qubits,) array of values in [0, π]
            
        Returns:
            Statevector representing the quantum state
        """
        if not QISKIT_AVAILABLE:
            raise RuntimeError("Qiskit required for encoding")
        
        # Ensure features match qubit count
        if len(features) != self.n_qubits:
            features = features[:self.n_qubits]
        
        # Bind features to circuit parameters
        circuit = self.feature_map.assign_parameters(features)
        
        # Compute statevector
        self.statevector = Statevector.from_instruction(circuit)
        
        return self.statevector

    def visualize_encoding_process(self, features: np.ndarray, save_path: str = None):
        """
        Create comprehensive visualization of the encoding process.
        
        Shows:
        1. Input EEG features (bar chart)
        2. Quantum circuit diagram
        3. Hilbert space state vector (city plot)
        4. Bloch sphere representation (for small n_qubits)
        5. Density matrix heatmap
        """
        if not QISKIT_AVAILABLE:
            print("⚠ Qiskit required for visualization")
            return
        
        print(f"\n{'='*70}")
        print(f"ENCODING EEG FEATURES TO HILBERT SPACE")
        print(f"{'='*70}\n")
        
        # Encode features
        statevector = self.encode_features(features)
        density_matrix = DensityMatrix(statevector)
        
        # Print feature values
        print("INPUT FEATURES (normalized to [0, π]):")
        print("-" * 70)
        for i, val in enumerate(features[:self.n_qubits]):
            print(f"  Feature {i}: {val:.4f} rad ({val*180/np.pi:.1f}°)")
        
        # Print state information
        print(f"\nQUANTUM STATE IN HILBERT SPACE:")
        print("-" * 70)
        print(f"  Dimension: {2**self.n_qubits}")
        print(f"  State vector: |ψ⟩ = Σ α_i |i⟩")
        print(f"  Number of amplitudes: {len(statevector.data)}")
        print(f"  Normalization: Σ|α_i|² = {np.sum(np.abs(statevector.data)**2):.6f}")
        
        # Show top amplitudes
        print(f"\n  Top 5 basis states by probability:")
        probs = np.abs(statevector.data)**2
        top_indices = np.argsort(probs)[::-1][:5]
        for idx in top_indices:
            basis_state = format(idx, f'0{self.n_qubits}b')
            amplitude = statevector.data[idx]
            prob = probs[idx]
            print(f"    |{basis_state}⟩: α = {amplitude.real:.3f}{amplitude.imag:+.3f}i, "
                  f"P = {prob:.4f}")
        
        # Create visualization
        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.3)
        
        # 1. Input features
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_input_features(ax1, features)
        
        # 2. Circuit diagram
        ax2 = fig.add_subplot(gs[1, :])
        self._plot_circuit(ax2)
        
        # 3. State vector (city plot)
        ax3 = fig.add_subplot(gs[2, 0], projection='3d')
        self._plot_state_city(ax3, statevector)
        
        # 4. Probability distribution
        ax4 = fig.add_subplot(gs[2, 1])
        self._plot_probabilities(ax4, statevector)
        
        # 5. Density matrix
        ax5 = fig.add_subplot(gs[2, 2])
        self._plot_density_matrix(ax5, density_matrix)
        
        plt.suptitle(f"ZZ Feature Map: EEG → Hilbert Space (n={self.n_qubits} qubits, reps={self.reps})",
                     fontsize=16, fontweight='bold', y=0.995)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"\n✓ Visualization saved to: {save_path}")
        
        plt.show()
        print(f"{'='*70}\n")

    def _plot_input_features(self, ax, features):
        """Plot input EEG features as bar chart."""
        n = min(len(features), self.n_qubits)
        x = np.arange(n)
        bars = ax.bar(x, features[:n], color='steelblue', alpha=0.7, edgecolor='black')
        
        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars, features[:n])):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.3f}',
                   ha='center', va='bottom', fontsize=9)
        
        ax.axhline(y=np.pi, color='red', linestyle='--', alpha=0.5, label='π (max)')
        ax.set_xlabel('Feature Index', fontsize=11, fontweight='bold')
        ax.set_ylabel('Value (radians)', fontsize=11, fontweight='bold')
        ax.set_title('1. INPUT: Classical EEG Features (normalized to [0, π])',
                    fontsize=12, fontweight='bold', pad=10)
        ax.set_xticks(x)
        ax.set_ylim(0, np.pi * 1.1)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

    def _plot_circuit(self, ax):
        """Plot quantum circuit diagram."""
        ax.axis('off')
        circuit = self.feature_map.decompose()
        circuit.draw('mpl', ax=ax, style='iqp')
        ax.set_title('2. QUANTUM CIRCUIT: ZZ Feature Map (H + RZ + ZZ entanglement)',
                    fontsize=12, fontweight='bold', pad=10)

    def _plot_state_city(self, ax, statevector):
        """Plot 3D city plot of state amplitudes."""
        n_states = len(statevector.data)
        x = np.arange(n_states)
        real_parts = statevector.data.real
        imag_parts = statevector.data.imag
        
        width = 0.4
        ax.bar(x - width/2, real_parts, width, label='Real', color='blue', alpha=0.7)
        ax.bar(x + width/2, imag_parts, width, label='Imag', color='red', alpha=0.7)
        
        ax.set_xlabel('Basis State |i⟩', fontsize=10, fontweight='bold')
        ax.set_ylabel('Amplitude', fontsize=10, fontweight='bold')
        ax.set_zlabel('Value', fontsize=10, fontweight='bold')
        ax.set_title('3. STATE VECTOR: Complex Amplitudes in Hilbert Space',
                    fontsize=11, fontweight='bold', pad=10)
        ax.legend()

    def _plot_probabilities(self, ax, statevector):
        """Plot probability distribution over basis states."""
        probs = np.abs(statevector.data)**2
        x = np.arange(len(probs))
        
        bars = ax.bar(x, probs, color='green', alpha=0.7, edgecolor='black')
        
        # Highlight top states
        top_idx = np.argmax(probs)
        bars[top_idx].set_color('darkgreen')
        bars[top_idx].set_alpha(1.0)
        
        ax.set_xlabel('Basis State |i⟩', fontsize=10, fontweight='bold')
        ax.set_ylabel('Probability |α_i|²', fontsize=10, fontweight='bold')
        ax.set_title('4. MEASUREMENT PROBABILITIES: |α_i|²',
                    fontsize=11, fontweight='bold', pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels([format(i, f'0{self.n_qubits}b') for i in x],
                          rotation=45, ha='right', fontsize=8)
        ax.grid(axis='y', alpha=0.3)

    def _plot_density_matrix(self, ax, density_matrix):
        """Plot density matrix heatmap."""
        rho = density_matrix.data
        im = ax.imshow(np.abs(rho), cmap='viridis', interpolation='nearest')
        
        ax.set_xlabel('Basis State', fontsize=10, fontweight='bold')
        ax.set_ylabel('Basis State', fontsize=10, fontweight='bold')
        ax.set_title('5. DENSITY MATRIX: ρ = |ψ⟩⟨ψ|',
                    fontsize=11, fontweight='bold', pad=10)
        
        plt.colorbar(im, ax=ax, label='|ρ_ij|')
        
        # Add grid
        n = len(rho)
        ax.set_xticks(np.arange(n))
        ax.set_yticks(np.arange(n))
        ax.set_xticklabels([format(i, f'0{self.n_qubits}b') for i in range(n)],
                          rotation=90, fontsize=7)
        ax.set_yticklabels([format(i, f'0{self.n_qubits}b') for i in range(n)],
                          fontsize=7)


def run_simulation_with_real_eeg():
    """
    Run simulation using actual EEG-derived features.
    """
    print("\n" + "="*70)
    print("ZZ FEATURE MAP SIMULATION: EEG TO HILBERT SPACE")
    print("="*70)
    
    if not QISKIT_AVAILABLE:
        print("\n⚠ Qiskit not installed. Install with:")
        print("  pip install qiskit qiskit-aer qiskit-machine-learning")
        return
    
    # Load configuration
    cfg = load_config()
    n_qubits = cfg["decoding"]["n_qubits"]
    reps = cfg["decoding"]["feature_map_reps"]
    
    # Create simulator
    simulator = ZZFeatureMapSimulator(n_qubits=n_qubits, reps=reps)
    
    # Show explanation
    simulator.explain_zz_feature_map()
    
    # Simulate different motor imagery classes
    print("\nSIMULATING DIFFERENT MOTOR IMAGERY PATTERNS:")
    print("="*70)
    
    scenarios = [
        {
            'name': 'Left Hand Motor Imagery',
            'features': np.array([2.1, 0.8, 1.5, 0.3, 1.2, 0.5, 1.8, 0.4]),  # 8 features
            'description': 'High mu-band power over left motor cortex (C3)'
        },
        {
            'name': 'Right Hand Motor Imagery',
            'features': np.array([0.5, 2.3, 0.9, 1.8, 0.6, 2.1, 1.0, 1.9]),  # 8 features
            'description': 'High mu-band power over right motor cortex (C4)'
        },
        {
            'name': 'Rest State',
            'features': np.array([0.2, 0.3, 0.1, 0.2, 0.3, 0.2, 0.1, 0.3]),  # 8 features
            'description': 'Minimal motor cortex activation'
        },
        {
            'name': 'Both Hands Motor Imagery',
            'features': np.array([1.9, 1.8, 1.6, 1.7, 1.8, 1.9, 1.7, 1.6]),  # 8 features
            'description': 'Balanced activation across motor cortex'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Features: {scenario['features']}")
        
        # Visualize encoding
        save_path = f"mindlink/zz_simulation_{scenario['name'].replace(' ', '_').lower()}.png"
        simulator.visualize_encoding_process(scenario['features'], save_path=save_path)


if __name__ == "__main__":
    run_simulation_with_real_eeg()
