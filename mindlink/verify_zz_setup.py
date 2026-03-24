"""
Quick verification script to check if ZZ feature map simulation can run.
"""

import sys

def check_imports():
    """Check if all required packages are available."""
    print("Checking dependencies...")
    print("-" * 70)
    
    required = {
        'numpy': 'NumPy',
        'matplotlib': 'Matplotlib',
        'yaml': 'PyYAML',
        'qiskit': 'Qiskit',
        'qiskit_aer': 'Qiskit Aer',
        'qiskit_machine_learning': 'Qiskit Machine Learning'
    }
    
    missing = []
    for module, name in required.items():
        try:
            __import__(module)
            print(f"✓ {name:30} installed")
        except ImportError:
            print(f"✗ {name:30} MISSING")
            missing.append(name)
    
    print("-" * 70)
    
    if missing:
        print(f"\n⚠ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("\n✓ All dependencies installed!")
        return True


def test_zz_feature_map():
    """Test basic ZZ feature map functionality."""
    print("\nTesting ZZ Feature Map...")
    print("-" * 70)
    
    try:
        from qiskit.circuit.library import ZZFeatureMap
        from qiskit.quantum_info import Statevector
        import numpy as np
        
        # Create feature map
        n_qubits = 4
        reps = 2
        feature_map = ZZFeatureMap(
            feature_dimension=n_qubits,
            reps=reps,
            entanglement='linear'
        )
        print(f"✓ Created ZZFeatureMap: {n_qubits} qubits, {reps} reps")
        
        # Test encoding
        features = np.array([2.1, 0.8, 1.5, 0.3])
        circuit = feature_map.assign_parameters(features)
        statevector = Statevector.from_instruction(circuit)
        
        print(f"✓ Encoded features: {features}")
        print(f"✓ Quantum state dimension: {len(statevector.data)}")
        print(f"✓ Normalization: Σ|α|² = {np.sum(np.abs(statevector.data)**2):.6f}")
        
        # Show top amplitudes
        probs = np.abs(statevector.data)**2
        top_idx = np.argmax(probs)
        print(f"✓ Top basis state: |{format(top_idx, '04b')}⟩ with P={probs[top_idx]:.4f}")
        
        print("-" * 70)
        print("✓ ZZ Feature Map working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("-" * 70)
        return False


def main():
    print("\n" + "="*70)
    print("ZZ FEATURE MAP SETUP VERIFICATION")
    print("="*70 + "\n")
    
    # Check imports
    if not check_imports():
        sys.exit(1)
    
    # Test functionality
    if not test_zz_feature_map():
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✓ SETUP VERIFIED - Ready to run simulations!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Run interactive demo: python interactive_zz_demo.py")
    print("  2. Run full simulation: python zz_feature_map_simulation.py")
    print("  3. Read the guide: ZZ_FEATURE_MAP_GUIDE.md")
    print()


if __name__ == "__main__":
    main()
