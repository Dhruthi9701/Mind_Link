# Quick Start Guide - Quantum 3D Visualization

## Installation (2 minutes)

### Step 1: Install Dependencies

```bash
cd quantum_simulation
pip install -r requirements.txt
```

### Step 2: Run the Visualization

**Windows:**
```bash
run_visualization.bat
```

**Mac/Linux:**
```bash
python quantum_3d_viz.py
```

## What You'll See

### 🎬 5-Stage Journey

1. **EEG Signals** (3 seconds)
   - Watch real-time brain signals from motor cortex
   - See C3 (left) and C4 (right) channels

2. **Feature Extraction** (2 seconds)
   - Classical features extracted: mu and beta band power
   - 4 features normalized to [0, π]

3. **Quantum Encoding** (2 seconds)
   - Features encoded into quantum circuit
   - ZZ feature map creates superposition and entanglement

4. **Hilbert Space** (3 seconds) ⭐ **MAIN ATTRACTION**
   - 3D visualization of 16-dimensional quantum state
   - Rotate camera to explore from all angles
   - See probability distribution across basis states

5. **Pattern Comparison** (4 seconds)
   - Compare all 4 motor imagery patterns side-by-side
   - Quantum kernel matrix shows similarities

## 🎮 Essential Controls

| Key | What It Does |
|-----|--------------|
| **SPACE** | Go to next stage (most important!) |
| **1, 2, 3, 4** | Switch between Left, Right, Rest, Both Hands |
| **Mouse drag** | Rotate the 3D view |
| **C** | Toggle auto-rotation |
| **R** | Restart from beginning |

## 💡 Pro Tips

### First Time Users

1. **Let it play**: Press SPACE to advance through all 5 stages
2. **Go back to Stage 4**: Press R, then SPACE 3 times
3. **Rotate the view**: Drag with mouse to see 3D structure
4. **Try different patterns**: Press 1, 2, 3, 4 to compare

### Understanding Stage 4 (Hilbert Space)

This is where quantum magic happens!

- **Each bar** = One basis state (like |0101⟩)
- **Height** = Probability of measuring that state
- **Taller bars** = More likely outcomes
- **16 bars total** = 2⁴ = 16-dimensional space

**What to look for:**
- Left Hand: Tall bars on left side
- Right Hand: Tall bars on right side
- Rest: Evenly distributed
- Both Hands: Tall bars in center

### Understanding Stage 5 (Comparison)

The **Quantum Kernel Matrix** shows how similar states are:

```
              Left   Right  Rest   Both
Left Hand     1.000  0.234  0.189  0.457
Right Hand    0.234  1.000  0.165  0.412
```

- **1.000** = Identical (diagonal)
- **< 0.3** = Very different (good for classification!)
- **> 0.7** = Very similar (hard to tell apart)

## 🎯 Learning Path

### Beginner (5 minutes)
1. Run the visualization
2. Press SPACE to go through all stages
3. Try pressing 1, 2, 3, 4 to see different patterns

### Intermediate (15 minutes)
1. Focus on Stage 4 - rotate the camera
2. Compare how different patterns look in 3D
3. Study the quantum kernel matrix in Stage 5

### Advanced (30 minutes)
1. Read the full README.md
2. Check out the code in quantum_3d_viz.py
3. Modify parameters (number of qubits, repetitions)
4. Read ZZ_FEATURE_MAP_GUIDE.md in parent directory

## 🐛 Common Issues

### "pygame not found"
```bash
pip install pygame
```

### "Qiskit not available"
The visualization will work with mock quantum states. For real quantum simulation:
```bash
pip install qiskit qiskit-aer
```

### Visualization is slow
- Press C to disable auto-rotation
- Close other applications
- Reduce FPS in code (line: `FPS = 30` → `FPS = 20`)

### Can't see 3D bars
- Make sure you're on Stage 3, 4, or 5
- Try zooming out (scroll down)
- Press R to reset

## 📚 Next Steps

After exploring the visualization:

1. **Run the interactive demo**:
   ```bash
   cd ..
   python interactive_zz_demo.py
   ```

2. **Generate static visualizations**:
   ```bash
   python zz_feature_map_simulation.py
   ```

3. **Train the quantum model**:
   ```bash
   python train_models.py
   ```

4. **Run the full BCI pipeline**:
   ```bash
   python main.py
   ```

## 🎓 Educational Notes

### For Students

This visualization shows:
- How brain signals become quantum states
- Why quantum computing helps with pattern recognition
- What "Hilbert space" actually looks like
- How entanglement captures correlations

### For Teachers

Use this to demonstrate:
- Quantum superposition (Stage 3-4)
- Quantum entanglement (ZZ gates)
- Hilbert space geometry (Stage 4)
- Quantum kernels (Stage 5)
- Real-world quantum ML application

### For Researchers

Explore:
- Different feature maps (modify code)
- Various entanglement patterns
- Quantum kernel properties
- State separability metrics

## 🚀 Ready?

```bash
python quantum_3d_viz.py
```

Press SPACE and enjoy the journey from brain signals to quantum states! 🧠⚛️✨

---

**Questions?** Check README.md or the code comments!
