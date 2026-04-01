# Quantum 3D Visualization

Interactive 3D visualization showing how Mind Link transforms EEG signals into quantum states for classification.

## 🎯 What You'll See

This visualization takes you through 5 stages of the quantum BCI pipeline:

### Stage 1: EEG Signal Acquisition
- Real-time EEG signals from C3 (left motor cortex) and C4 (right motor cortex)
- Different patterns for left hand, right hand, rest, and both hands motor imagery

### Stage 2: Feature Extraction
- Extraction of mu band (8-13 Hz) and beta band (13-30 Hz) power
- 4 classical features: C3 μ, C4 μ, C3 β, C4 β
- Normalization to [0, π] for quantum encoding

### Stage 3: Quantum Encoding (ZZ Feature Map)
- 3D visualization of quantum circuit layers:
  - Hadamard gates creating superposition
  - RZ rotations encoding feature values
  - ZZ gates creating entanglement
- Watch features transform into quantum states

### Stage 4: Quantum State in Hilbert Space
- Full 3D visualization of 16-dimensional Hilbert space
- Each bar represents a basis state |0000⟩ to |1111⟩
- Height shows probability |αᵢ|²
- Color shows quantum phase
- Interactive rotation to explore from all angles

### Stage 5: Pattern Comparison
- Side-by-side comparison of all 4 motor imagery patterns
- Quantum kernel matrix showing state similarities
- Understand how quantum states separate different classes

## 🚀 Quick Start

```bash
# Install dependencies
pip install pygame numpy scipy qiskit qiskit-aer

# Run the visualization
cd quantum_simulation
python quantum_3d_viz.py
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| **SPACE** | Advance to next stage |
| **R** | Reset to beginning |
| **C** | Toggle auto-rotate camera |
| **Mouse drag** | Manually rotate view |
| **Scroll** | Zoom in/out |
| **1** | Show Left Hand pattern |
| **2** | Show Right Hand pattern |
| **3** | Show Rest pattern |
| **4** | Show Both Hands pattern |
| **P** | Pause/Resume animation |
| **ESC** | Quit |

## 📊 Understanding the Visualization

### Hilbert Space (Stage 4)

The 3D bars represent the quantum state in a 16-dimensional complex vector space:

- **X-Z plane**: Basis states arranged in a 4×4 grid
- **Y axis (height)**: Probability of measuring each basis state
- **Color intensity**: Amplitude magnitude
- **Grid**: Shows the structure of Hilbert space

For 4 qubits, we have 2⁴ = 16 basis states:
```
|0000⟩, |0001⟩, |0010⟩, |0011⟩, ...  |1111⟩
```

The quantum state is a superposition:
```
|ψ⟩ = α₀|0000⟩ + α₁|0001⟩ + ... + α₁₅|1111⟩
```

Where each αᵢ is a complex number (amplitude) and Σ|αᵢ|² = 1.

### Quantum Kernel Matrix (Stage 5)

Shows similarity between quantum states using the quantum kernel:
```
K(x, x') = |⟨ψ(x)|ψ(x')⟩|²
```

- **Diagonal = 1.0**: Each state is identical to itself
- **Low values (< 0.3)**: States are distinguishable → good for classification
- **High values (> 0.7)**: States are similar → hard to distinguish

Example:
```
              Left   Right  Rest   Both
Left Hand     1.000  0.234  0.189  0.457
Right Hand    0.234  1.000  0.165  0.412
Rest          0.189  0.165  1.000  0.288
Both Hands    0.457  0.412  0.288  1.000
```

Left and Right hands have low similarity (0.234) → easily distinguishable!

## 🧠 The Science Behind It

### Why Quantum Computing for BCI?

1. **Exponential Hilbert Space**
   - 4 classical features → 16-dimensional quantum state
   - More room to separate different motor imagery patterns

2. **Natural Entanglement**
   - EEG features are naturally correlated (C3 ↔ C4, mu ↔ beta)
   - ZZ gates create quantum correlations matching these relationships

3. **Quantum Interference**
   - Constructive/destructive interference encodes patterns
   - Quantum kernel detects patterns classical methods might miss

### ZZ Feature Map Circuit

```
q0: ─H─RZ(x₀)─■─────────────H─RZ(x₀)─■──────────
              │                       │
q1: ─H─RZ(x₁)─■─■───────────H─RZ(x₁)─■─■────────
                │                       │
q2: ─H─RZ(x₂)───■─■─────────H─RZ(x₂)───■─■──────
                  │                       │
q3: ─H─RZ(x₃)─────■─────────H─RZ(x₃)─────■──────
```

Where:
- **H**: Hadamard gate (creates superposition)
- **RZ(xᵢ)**: Rotation encoding feature value
- **■**: ZZ entanglement gate between qubits

Repeated 2× for deeper encoding.

## 🎨 Visual Features

### Color Coding

- **Quantum Blue** (Left Hand): High C3 activity
- **Quantum Purple** (Right Hand): High C4 activity
- **EEG Green** (Rest): High bilateral beta
- **Classical Orange** (Both Hands): Bilateral mu suppression

### 3D Effects

- **Glow effects**: Highlight high-probability states
- **Depth sorting**: Proper 3D rendering with occlusion
- **Smooth rotation**: Auto-rotate or manual control
- **Grid floor**: Shows Hilbert space structure

## 🔬 Technical Details

### Quantum State Encoding

Input features (4 values in [0, π]):
```python
features = [C3_mu, C4_mu, C3_beta, C4_beta]
```

ZZ Feature Map creates quantum state:
```python
from qiskit.circuit.library import ZZFeatureMap
feature_map = ZZFeatureMap(feature_dimension=4, reps=2, entanglement="linear")
circuit = feature_map.bind_parameters(features)
statevector = Statevector.from_instruction(circuit)
```

Output: 16 complex amplitudes representing quantum state in Hilbert space.

### Quantum Kernel

Measures similarity between two quantum states:
```python
def quantum_kernel(state1, state2):
    overlap = np.vdot(state1, state2)  # Inner product
    return np.abs(overlap) ** 2         # Squared magnitude
```

Used by QSVM (Quantum Support Vector Machine) for classification.

## 📚 Learn More

### Related Files
- `../ZZ_FEATURE_MAP_GUIDE.md` - Detailed guide on ZZ feature maps
- `../interactive_zz_demo.py` - Step-by-step interactive demo
- `../zz_feature_map_simulation.py` - Generate static visualizations
- `../decoding/quantum_path.py` - Quantum decoder implementation

### Papers
- Havlíček et al., "Supervised learning with quantum-enhanced feature spaces" (Nature 2019)
- Schuld & Killoran, "Quantum machine learning in feature Hilbert spaces" (PRL 2019)

### Qiskit Documentation
- [ZZFeatureMap](https://qiskit.org/documentation/stubs/qiskit.circuit.library.ZZFeatureMap.html)
- [Quantum Kernels](https://qiskit.org/documentation/machine-learning/tutorials/03_quantum_kernel.html)

## 🐛 Troubleshooting

### "Qiskit not available"
```bash
pip install qiskit qiskit-aer qiskit-machine-learning
```

The visualization will work with mock quantum states if Qiskit is not installed, but for real quantum simulation, install Qiskit.

### Performance Issues
- Reduce FPS in code: `FPS = 20` instead of 30
- Disable auto-rotate: Press **C**
- Use smaller quantum system (edit code to use 3 qubits instead of 4)

### Visualization Not Showing
```bash
pip install pygame
```

## 💡 Tips for Best Experience

1. **Start with Stage 1**: Press SPACE to advance through stages sequentially
2. **Explore Stage 4**: This is where the magic happens! Rotate the camera to see the 3D structure
3. **Compare Patterns**: Use keys 1-4 to switch between motor imagery patterns
4. **Study Stage 5**: Understand how quantum kernel separates different classes
5. **Pause and Observe**: Press P to pause and examine details

## 🎓 Educational Use

This visualization is perfect for:
- Understanding quantum machine learning concepts
- Teaching BCI signal processing
- Demonstrating quantum advantage in classification
- Exploring Hilbert space geometry
- Visualizing quantum entanglement

## 🤝 Contributing

Want to add more features?
- Additional visualization stages
- More motor imagery patterns
- Different quantum feature maps (Pauli, amplitude encoding)
- Real-time EEG integration
- VR/AR support

## 📞 Questions?

If you have questions about:
- **Quantum concepts**: See `ZZ_FEATURE_MAP_GUIDE.md`
- **Implementation**: Check `decoding/quantum_path.py`
- **Visualization**: Read the code comments in `quantum_3d_viz.py`

Enjoy exploring quantum BCI! 🧠⚛️✨
