"""
Generate all visualization results for Mind Link Phase 1
Run this script to create charts and graphs for the presentation
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec
import os

# Set style
plt.style.use('dark_background')
COLORS = {
    'quantum_blue': '#00B4FF',
    'quantum_purple': '#B480FF',
    'quantum_cyan': '#00FFC8',
    'quantum_pink': '#FF64B4',
    'eeg_green': '#50FF78',
    'classical_orange': '#FFA028',
    'highlight': '#FFDC00',
    'bg': '#080A14'
}

# Create output directories
os.makedirs('1_signal_isolation', exist_ok=True)
os.makedirs('2_zz_encoding', exist_ok=True)
os.makedirs('3_motor_imagery', exist_ok=True)
os.makedirs('4_latency_metrics', exist_ok=True)
os.makedirs('5_protocol_synthesis', exist_ok=True)

print("Generating Phase 1 visualizations...")
print("=" * 60)
