# ZZ Feature Map Simulation - Quick Start

## 📦 What I Created for You

I've created a complete simulation suite to show you how EEG signals are mapped to Hilbert space using ZZ feature maps. Here's what you have:

### 1. **Interactive Demo** (Best to start here!)
**File:** `interactive_zz_demo.py`

```bash
cd mindlink
python interactive_zz_demo.py
```

**What it does:**
- 5-step walkthrough with detailed explanations
- Press Enter to advance through each step
- Shows visualizations at each stage
- Compares different motor imagery classes
- **Perfect for learning the concepts!**

---

### 2. **Comprehensive Simulation**
**File:** `zz_feature_map_simulation.py`

```bash
python zz_feature_map_simulation.py
```

**What it does:**
- Simulates 4 motor imagery scenarios:
  - Left hand movement
  - Right hand movement
  - Rest state
  - Both hands movement
- Generates detailed visualizations for each
- Shows circuit diagrams, state vectors, density matrices
- Saves PNG files for documentation

---

### 3. **Complete Guide**
**File:** `ZZ_FEATURE_MAP_GUIDE.md`

- Comprehensive explanation of every concept
- Mathematical details
- Interpretation of visualizations
- Troubleshooting tips
- Further reading resources

---

### 4. **Setup Verification**
**File:** `verify_zz_setup.py`

```bash
python verify_zz_setup.py
```

**What it does:**
- Checks if all dependencies are installed
- Tests basic ZZ feature map functionality
- Confirms everything is working

---

### 5. **Flow Diagram Generator**
**File:** `create_zz_flow_diagram.py`

```bash
python create_zz_flow_diagram.py
```

**What it does:**
- Creates a visual flow diagram
- Shows the complete pipeline: EEG → Features → Quantum State → Classification
- Saves high-resolution PNG

---

## 🚀 Quick Start (3 Steps)

### Step 1: Verify Setup
```bash
cd mindlink
python verify_zz_setup.py
```

If you see errors, install dependencies:
```bash
pip install -r requirements.txt
```

### Step 2: Run Interactive Demo
```bash
python interactive_zz_demo.py
```

Follow along and press Enter to advance through each step.

### Step 3: Run Full Simulation
```bash
python zz_feature_map_simulation.py
```

This will generate detailed visualizations for all motor imagery classes.

---

## 📊 What You'll See

### Visualizations Include:

1. **Input Features (Bar Chart)**
   - Your 4 EEG features normalized to [0, π]
   - Shows which motor cortex regions are active

2. **Quantum Circuit Diagram**
   - Visual representation of the ZZ feature map
   - Shows H gates, RZ rotations, and ZZ entanglement gates

3. **State Vector (3D Plot)**
   - 16 complex amplitudes in Hilbert space
   - Real and imaginary parts shown separately

4. **Measurement Probabilities**
   - Probability of measuring each basis state
   - Shows quantum superposition distribution

5. **Density Matrix**
   - Heatmap showing quantum state structure
   - Diagonal = probabilities, off-diagonal = coherences

---

## 🧠 Key Concepts Explained

### What is Hilbert Space?
- A complex vector space where quantum states live
- For 4 qubits: dimension = 2⁴ = 16
- Each point is a quantum state |ψ⟩

### What is the ZZ Feature Map?
A quantum circuit with 3 layers:

1. **Hadamard Gates (H)**: Create superposition
2. **RZ Rotations**: Encode your EEG features as quantum phases
3. **ZZ Gates**: Create entanglement between qubits

These layers repeat 2 times (reps=2) for deeper encoding.

### Why Use Quantum Encoding?
- **Exponential space**: 4 features → 16-dimensional quantum state
- **Entanglement**: Captures correlations between EEG features naturally
- **Quantum interference**: Encodes patterns classical methods might miss
- **Quantum kernel**: Measures similarity via quantum state overlap

---

## 📈 Example Output

When you run the simulation for "Left Hand Motor Imagery":

**Input Features:**
```
Feature 0: 2.100 rad  (High C3 mu power - left motor cortex)
Feature 1: 0.800 rad  (Low C4 mu power)
Feature 2: 1.500 rad  (Moderate C3 beta power)
Feature 3: 0.300 rad  (Low C4 beta power)
```

**Quantum State (Top basis states):**
```
|0110⟩: P = 0.0792
|1010⟩: P = 0.0571
|0010⟩: P = 0.0446
...
```

The quantum state is a superposition of all 16 basis states, with the distribution determined by your input features!

---

## 🎯 What Each Simulation Shows

### Left Hand Motor Imagery
- High activity in left motor cortex (C3)
- Quantum state reflects this asymmetry
- Distinct pattern in Hilbert space

### Right Hand Motor Imagery
- High activity in right motor cortex (C4)
- Different quantum state distribution
- Separable from left hand in quantum kernel

### Rest State
- Low activity across all channels
- Quantum state concentrated near |0000⟩
- Clearly distinguishable from active states

### Both Hands Motor Imagery
- Bilateral motor cortex activation
- Balanced quantum state distribution
- Unique pattern in Hilbert space

---

## 🔬 Understanding the Output

### State Vector Amplitudes
Each amplitude αᵢ is a complex number:
- **Real part**: Contributes to measurement probability
- **Imaginary part**: Encodes quantum phase
- **Magnitude |αᵢ|²**: Probability of measuring basis state |i⟩

### Quantum Kernel Matrix
Shows similarity between different motor imagery patterns:
```
K(x, x') = |⟨ψ(x)|ψ(x')⟩|²
```
- Diagonal = 1.0 (state with itself)
- Off-diagonal < 1.0 (different states)
- Lower values = more distinguishable classes

---

## 🛠️ Customization

Want to experiment? Edit `config.yaml`:

```yaml
decoding:
  n_qubits: 4              # Number of features (2-8 recommended)
  feature_map_reps: 2      # Circuit repetitions (1-3)
  entanglement: "linear"   # "linear", "full", or "circular"
  max_circuit_depth: 30    # Target circuit depth
```

Then re-run the simulations to see how changes affect the quantum states!

---

## 📚 Files Generated

After running the simulations, you'll have:

- `zz_encoding_demo.png` - Basic encoding visualization
- `zz_simulation_left_hand_motor_imagery.png` - Left hand detailed view
- `zz_simulation_right_hand_motor_imagery.png` - Right hand detailed view
- `zz_simulation_rest_state.png` - Rest state detailed view
- `zz_simulation_both_hands_motor_imagery.png` - Both hands detailed view
- `zz_feature_map_flow.png` - Complete pipeline diagram
- `quantum_circuit.png` - Circuit diagram (from quantum_path.py)

---

## 🐛 Troubleshooting

### "Qiskit not available"
```bash
pip install qiskit qiskit-aer qiskit-machine-learning
```

### "Config file not found"
Make sure you're in the `mindlink/` directory when running scripts.

### Visualizations not showing
```bash
pip install matplotlib
```

### Need more explanation?
Read `ZZ_FEATURE_MAP_GUIDE.md` for comprehensive details!

---

## 💡 Next Steps

1. ✅ Run `verify_zz_setup.py` to check your setup
2. ✅ Run `interactive_zz_demo.py` to learn the concepts
3. ✅ Run `zz_feature_map_simulation.py` for detailed analysis
4. ✅ Run `create_zz_flow_diagram.py` for a visual overview
5. ✅ Read `ZZ_FEATURE_MAP_GUIDE.md` for deep dive
6. ✅ Experiment with different configurations in `config.yaml`
7. ✅ Train your quantum model: `python train_models.py`
8. ✅ Test real-time inference: `python real_time_inference.py`

---

## 🎓 Learning Path

**Beginner:**
1. Run interactive demo
2. Read the console output carefully
3. Look at the generated visualizations

**Intermediate:**
1. Run full simulation
2. Compare different motor imagery patterns
3. Examine the quantum kernel matrix

**Advanced:**
1. Read the complete guide
2. Modify circuit parameters in config.yaml
3. Analyze how changes affect quantum states
4. Dive into the source code

---

## ❓ Questions to Explore

As you run the simulations, think about:

1. How do different EEG features affect the quantum state?
2. Why do different motor imagery patterns produce different quantum states?
3. How does entanglement help capture feature correlations?
4. What role does quantum interference play?
5. How does the quantum kernel measure similarity?

The simulations are designed to help you answer these questions visually!

---

## 📞 Need More Data?

If you want to see:
- Different feature values → Modify the `scenarios` in `zz_feature_map_simulation.py`
- More qubits → Change `n_qubits` in `config.yaml`
- Different entanglement → Change `entanglement` in `config.yaml`
- Real EEG data → Run `train_models.py` to use actual PhysioNet data

---

## 🎉 Summary

You now have:
- ✅ Interactive learning tool
- ✅ Comprehensive simulation suite
- ✅ Detailed documentation
- ✅ Visual flow diagrams
- ✅ Setup verification
- ✅ Customization options

Everything you need to understand how EEG signals map to Hilbert space using ZZ feature maps!

**Start with:** `python interactive_zz_demo.py`

Enjoy exploring quantum BCI! 🧠⚛️
