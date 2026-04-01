"""Generate Frequency Spectrum visualizations"""
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

plt.style.use('dark_background')

print("Generating Frequency Spectrum visualizations...")

# Generate signals
fs = 500  # Sampling frequency
t = np.linspace(0, 2, fs * 2)

# Raw signal with artifacts
raw_signal = 10 * np.sin(2 * np.pi * 10 * t) + \
             5 * np.sin(2 * np.pi * 50 * t) + \
             np.random.normal(0, 8, len(t))

# Clean signal (Mu-rhythm)
clean_signal = 10 * np.sin(2 * np.pi * 10 * t)

# Compute FFT
freq_raw, psd_raw = signal.welch(raw_signal, fs, nperseg=256)
freq_clean, psd_clean = signal.welch(clean_signal, fs, nperseg=256)

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
fig.patch.set_facecolor('#080A14')

# Raw spectrum
ax1.semilogy(freq_raw, psd_raw, color='#FF6B6B', linewidth=2)
ax1.axvspan(8, 13, alpha=0.3, color='#00FFC8', label='Mu Band (8-13 Hz)')
ax1.axvspan(48, 52, alpha=0.3, color='#FF6B6B', label='Power Line (50 Hz)')
ax1.set_title('BEFORE: Frequency Spectrum (Raw)', fontsize=14, fontweight='bold')
ax1.set_ylabel('Power Spectral Density', fontsize=12)
ax1.set_xlim(0, 60)
ax1.grid(True, alpha=0.2)
ax1.legend()

# Clean spectrum
ax2.semilogy(freq_clean, psd_clean, color='#00FFC8', linewidth=2)
ax2.axvspan(8, 13, alpha=0.3, color='#00FFC8', label='Mu Band (8-13 Hz) - Isolated')
ax2.set_title('AFTER: Frequency Spectrum (Processed)', fontsize=14, fontweight='bold')
ax2.set_xlabel('Frequency (Hz)', fontsize=12)
ax2.set_ylabel('Power Spectral Density', fontsize=12)
ax2.set_xlim(0, 60)
ax2.grid(True, alpha=0.2)
ax2.legend()

plt.tight_layout()
plt.savefig('1_signal_isolation/frequency_spectrum_comparison.png', dpi=300, bbox_inches='tight', facecolor='#080A14')
print("✓ Saved: frequency_spectrum_comparison.png")
plt.close()
