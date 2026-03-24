# ZZ Feature Map: EEG to Hilbert Space Mapping Guide

## Overview

This guide explains how your MindLink system maps classical EEG signals to quantum states in Hilbert space using the **ZZ Feature Map**. Two simulation scripts are provided to help you understand every aspect of this quantum encoding process.

---

## 🎯 What You'll Learn

1. **How classical EEG features become quantum states**
2. **What Hilbert space is and why it matters**
3. **How ZZ feature maps create entanglement**
4. **Why quantum encoding helps with motor imagery classification**
5. **Visual representation of quantum states**

---

## 📋 Prerequisites

Install required packages:

```bash
pip install qiskit qiskit-aer qiskit-machine-learning matplotlib numpy pyyaml
```

---

## 🚀 Quick Start

### Option 1: Interactive Step-by-Step Demo (Recommended for Learning)

```bash
cd mindlink
python interactive_zz_demo.py
```

**What it does:**
- Walks you through 5 steps with explanations
- Press Enter to advance through each step
- Shows visualizations of the encoding process
- Compares different motor imagery classes
- **Best for**: Understanding the concepts

**Steps covered:**
1. EEG features (classical data)
2. Hilbert space explanation
3. ZZ feature map circuit structure
4. Encoding process visualization
5. Comparing different motor imagery patterns

---

### Option 2: Comprehensive Simulation (For Deep Analysis)

```bash
cd mindlink
python zz_feature_map_simulation.py
```

**What it does:**
- Runs complete simulations for 4 motor imagery scenarios
- Generates detailed visualizations for each
- Shows circuit diagrams, state vectors, density matrices
- Saves PNG files for each scenario
- **Best for**: Detailed analysis and documentation

**Output files:**
- `zz_simulation_left_hand_motor_imagery.png`
- `zz_simulation_right_hand_motor_imagery.png`
- `zz_simulation_rest_state.png`
- `zz_simulation_both_hands_motor_imagery.png`

---

## 🧠 Understanding the ZZ Feature Map

### The Big Picture

```
Classical EEG Features (4 numbers)
         ↓
   ZZ Feature Map
         ↓
Quantum State in Hilbert Space (16 complex amplitudes)
         ↓
   Quantum Kernel
         ↓
    Classification
```

### Key Components

#### 1. **Input: EEG Features**
- Extracted from motor cortex channels (C3, C4)
- Features include:
  - CSP (Common Spatial Patterns) components
  - Mu band power (8-13 Hz)
  - Beta band power (13-30 Hz)
- Normalized to [0, π] range

#### 2. **ZZ Feature Map Circuit**

The circuit has 3 layers per repetition:

**Layer 1: Hadamard Gates (H)**
```
H|0⟩ = (|0⟩ + |1⟩)/√2
```
- Creates superposition on all qubits
- Prepares qubits for encoding

**Layer 2: RZ Rotations**
```
RZ(φ) = exp(-iφZ/2)
```
- Each qubit rotated by corresponding feature value
- Encodes classical data as quantum phases
- φ = feature value (in radians)

**Layer 3: ZZ Entanglement**
```
ZZ(φ) = exp(-iφZ⊗Z/2)
```
- Creates quantum correlations between qubits
- Applied to neighboring pairs: (q0,q1), (q1,q2), (q2,q3)
- Angle: φ = (π - xᵢ)(π - xⱼ)
- Captures feature interactions

**Repetitions (reps=2)**
- Layers 1-3 repeated twice
- Increases expressiveness
- Deeper entanglement structure

#### 3. **Output: Quantum State in Hilbert Space**

For 4 qubits:
- **Dimension**: 2⁴ = 16
- **Basis states**: |0000⟩, |0001⟩, ..., |1111⟩
- **General state**: |ψ⟩ = Σᵢ αᵢ|i⟩
- **Constraint**: Σᵢ|αᵢ|² = 1

Each αᵢ is a complex number (amplitude) that encodes information about the input features through quantum interference.

---

## 📊 What the Visualizations Show

### 1. Input Features (Bar Chart)
- Shows the 4 classical EEG feature values
- Values in radians [0, π]
- Red dashed line indicates maximum (π)

### 2. Quantum Circuit Diagram
- Visual representation of the ZZ feature map
- Shows H gates, RZ rotations, and ZZ entanglement
- Read left to right (time evolution)

### 3. State Vector (3D City Plot)
- 16 bars representing complex amplitudes
- Blue = real part, Red = imaginary part
- Height shows amplitude magnitude

### 4. Measurement Probabilities
- Probability of measuring each basis state
- |αᵢ|² for each basis state |i⟩
- Must sum to 1.0

### 5. Density Matrix
- Heatmap showing ρ = |ψ⟩⟨ψ|
- Diagonal = probabilities
- Off-diagonal = quantum coherences (interference)

---

## 🔬 Example: Left Hand Motor Imagery

**Input Features:**
```
Feature 0: 2.100 rad  (High C3 mu power - left motor cortex active)
Feature 1: 0.800 rad  (Low C4 mu power)
Feature 2: 1.500 rad  (Moderate C3 beta power)
Feature 3: 0.300 rad  (Low C4 beta power)
```

**Quantum State (Top 5 basis states):**
```
|0110⟩: α = 0.234+0.156i, P = 0.0792
|1010⟩: α = 0.198-0.134i, P = 0.0571
|0010⟩: α = 0.187+0.098i, P = 0.0446
|1110⟩: α = 0.156-0.167i, P = 0.0523
|0100⟩: α = 0.145+0.123i, P = 0.0361
```

The quantum state is a superposition of all 16 basis states, with amplitudes determined by the input features and the ZZ feature map structure.

---

## 🎓 Why This Matters for BCI

### Classical vs Quantum Encoding

**Classical Approach:**
- Features → Feature vector in ℝⁿ
- Linear or kernel methods
- Limited expressiveness

**Quantum Approach:**
- Features → Quantum state in ℂ^(2ⁿ)
- Exponentially larger space
- Natural handling of correlations via entanglement
- Quantum kernel can detect patterns classical methods miss

### Advantages for Motor Imagery Classification

1. **Entanglement captures feature correlations**
   - EEG features naturally correlated (mu/beta bands, C3/C4)
   - ZZ gates create quantum correlations matching these

2. **Exponential Hilbert space**
   - 4 features → 16-dimensional quantum state
   - More room for separating classes

3. **Quantum interference**
   - Constructive/destructive interference encodes patterns
   - Quantum kernel measures similarity via state overlap

4. **Efficient for small feature sets**
   - Works well with 4-8 qubits (current hardware)
   - Perfect for motor imagery (few key features)

---

## 🔍 Understanding the Quantum Kernel

The quantum kernel measures similarity between quantum states:

```
K(x, x') = |⟨ψ(x)|ψ(x')⟩|²
```

Where:
- |ψ(x)⟩ = quantum state for features x
- ⟨ψ(x)|ψ(x')⟩ = inner product (overlap)
- |...|² = squared magnitude

**Properties:**
- K(x, x) = 1.0 (state with itself)
- 0 ≤ K(x, x') ≤ 1.0 (similarity measure)
- Lower values = more distinguishable

**Example kernel matrix:**
```
              Left Hand  Right Hand  Rest    Both Hands
Left Hand     1.0000     0.2341      0.1892  0.4567
Right Hand    0.2341     1.0000      0.1654  0.4123
Rest          0.1892     0.1654      1.0000  0.2876
Both Hands    0.4567     0.4123      0.2876  1.0000
```

The QSVM uses this kernel for classification!

---

## 🛠️ Customization

### Change Number of Qubits

Edit `config.yaml`:
```yaml
decoding:
  n_qubits: 4  # Change this (2-8 recommended)
```

### Change Repetitions

Edit `config.yaml`:
```yaml
decoding:
  feature_map_reps: 2  # More reps = deeper circuit
```

### Change Entanglement Pattern

Edit `config.yaml`:
```yaml
decoding:
  entanglement: "linear"  # Options: "linear", "full", "circular"
```

---

## 📚 Further Reading

### Papers
- **ZZ Feature Maps**: Havlíček et al., "Supervised learning with quantum-enhanced feature spaces" (Nature 2019)
- **Quantum Kernels**: Schuld & Killoran, "Quantum machine learning in feature Hilbert spaces" (PRL 2019)
- **BCI Applications**: Hur et al., "Quantum convolutional neural networks for multi-channel supervised learning" (2022)

### Qiskit Documentation
- [ZZFeatureMap](https://qiskit.org/documentation/stubs/qiskit.circuit.library.ZZFeatureMap.html)
- [Quantum Kernels](https://qiskit.org/documentation/machine-learning/tutorials/03_quantum_kernel.html)
- [QSVC](https://qiskit.org/documentation/machine-learning/stubs/qiskit_machine_learning.algorithms.QSVC.html)

---

## 🐛 Troubleshooting

### "Qiskit not available"
```bash
pip install qiskit qiskit-aer qiskit-machine-learning
```

### "Circuit depth exceeds target"
- Reduce `feature_map_reps` in config.yaml
- Use simpler entanglement pattern ("linear" instead of "full")

### Visualization not showing
```bash
pip install matplotlib
```

### "Config file not found"
- Make sure you're running from the `mindlink/` directory
- Check that `config.yaml` exists

---

## 💡 Next Steps

1. **Run the interactive demo** to understand the concepts
2. **Run the full simulation** to see detailed visualizations
3. **Train the quantum model**: `python train_models.py`
4. **Test real-time inference**: `python real_time_inference.py`
5. **Experiment with different configurations** in `config.yaml`

---

## 📞 Questions?

If you need more data or have questions about specific aspects:
- Check the inline comments in the simulation scripts
- Review the circuit diagrams generated
- Examine the state vector amplitudes
- Compare kernel matrices for different classes

The simulations are designed to be self-explanatory with detailed output at each step!
