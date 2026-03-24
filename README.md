# Mind_Link - Quantum Brain-Computer Interface

A hybrid quantum-classical Brain-Computer Interface (BCI) system for motor imagery classification using EEG signals and quantum machine learning.

## Overview

Mind_Link combines classical signal processing with quantum computing to decode motor imagery from EEG signals. The system uses:
- **Classical Path**: CSP + PSD feature extraction with SVM
- **Quantum Path**: ZZ Feature Map encoding with Quantum SVM (QSVM)
- **Hybrid Decoder**: Ensemble of both approaches

## Features

- 🧠 Real-time EEG signal processing
- ⚛️ Quantum feature encoding using ZZFeatureMap
- 🎯 Motor imagery classification (Left/Right/Both/Rest)
- 🚁 Drone control integration via MAVLink
- 📊 Comprehensive visualization tools
- 🔬 PhysioNet dataset support

## System Architecture

```
Raw EEG → Preprocessing → Feature Extraction (CSP+PSD) → Quantum Encoding (ZZ Feature Map) → QSVM → Classification
```

## Installation

### Prerequisites
- Python 3.8+
- Conda (recommended)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Dhruthi9701/Mind_Link.git
cd Mind_Link
```

2. Create conda environment:
```bash
conda create -n mind_link python=3.9
conda activate mind_link
```

3. Install dependencies:
```bash
cd mindlink
pip install -r requirements.txt
```

## Quick Start

### 1. Train Models
```bash
python train_models.py
```

### 2. Run ZZ Feature Map Simulation
```bash
python zz_feature_map_simulation.py
```

### 3. Real-time Inference
```bash
python real_time_inference.py
```

### 4. Drone Control (Simulation)
```bash
python drone_control/sim3d.py
```

## Project Structure

```
Mind_Link/
├── mindlink/
│   ├── config.yaml              # System configuration
│   ├── decoding/                # Decoder implementations
│   │   ├── classical_path.py    # Classical SVM decoder
│   │   ├── quantum_path.py      # Quantum SVM decoder
│   │   └── hybrid_decoder.py    # Hybrid ensemble
│   ├── processing/              # Signal processing
│   │   └── denoising_pipeline.py
│   ├── utils/                   # Utilities
│   │   └── feature_engineering.py
│   ├── drone_control/           # Drone integration
│   ├── input/                   # EEG input handling
│   ├── safety/                  # Safety mechanisms
│   └── transmission/            # MAVLink communication
├── docs/                        # Documentation
└── README.md
```

## Configuration

Edit `mindlink/config.yaml` to customize:
- Number of qubits (default: 8)
- Feature map repetitions (default: 1)
- EEG channels
- Frequency bands
- Classification parameters

## Quantum Feature Encoding

The system uses ZZFeatureMap to encode 8 classical EEG features into a 256-dimensional quantum Hilbert space:

1. **Hadamard Gates**: Create superposition
2. **RZ Rotations**: Encode feature values as quantum phases
3. **ZZ Entanglement**: Capture feature correlations

See `ZZ_FEATURE_MAP_GUIDE.md` for detailed explanation.

## Visualizations

The system generates several visualizations:
- `zz_encoding_demo.png` - Complete encoding process
- `zz_feature_map_flow.png` - Pipeline diagram
- `zz_simulation_*.png` - Motor imagery scenarios

## Dataset

The system supports:
- **PhysioNet EEGMMIDB**: Motor imagery dataset (auto-downloaded)
- **Custom EEG**: Via ITIE headcap integration

Download PhysioNet data:
```bash
python download_physionet_data.py
```

## Performance

- **Classical SVM**: ~62.5% CV accuracy
- **Quantum SVM**: Competitive performance with quantum advantage in feature space
- **Hybrid**: Ensemble of both approaches

## Hardware Integration

### Supported Devices
- ITIE EEG Headcap (via Bluetooth)
- OpenBCI boards
- Any LSL-compatible EEG device

### Drone Control
- MAVLink protocol support
- Tello drone integration
- 3D simulation environment

## Documentation

- `QUICK_START.txt` - Command reference
- `ZZ_FEATURE_MAP_GUIDE.md` - Quantum encoding explained
- `PHYSIONET_DOWNLOAD_GUIDE.md` - Dataset guide
- `DATASET_COMPARISON.md` - PhysioNet vs ITIE comparison

## Safety

The system includes multiple safety layers:
- Signal quality monitoring
- Confidence thresholds
- Emergency stop mechanisms
- Watchdog timers

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

[Add your license here]

## Citation

If you use this project in your research, please cite:

```bibtex
@software{mind_link_2024,
  title={Mind_Link: Quantum Brain-Computer Interface},
  author={[Your Name]},
  year={2024},
  url={https://github.com/Dhruthi9701/Mind_Link}
}
```

## Acknowledgments

- PhysioNet for the EEGMMIDB dataset
- Qiskit team for quantum computing framework
- MNE-Python for EEG processing tools

## Contact

[Add your contact information]

---

**Note**: This is a research project. Not intended for medical use.
