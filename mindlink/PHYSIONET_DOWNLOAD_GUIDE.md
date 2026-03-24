# PhysioNet Data Download Guide

## How Your Data Was Downloaded

When you ran `python train_models.py`, it automatically downloaded PhysioNet data using MNE's built-in downloader:

```python
# From feature_engineering.py
raw_files = eegbci.load_data(subject, runs, path="mindlink/data/physionet/")
```

This downloaded:
- **Subject 1** (default)
- **Runs 4, 8, 12** (motor imagery tasks)
- **3 EDF files** (~4.5 MB total)
- **Location**: `mindlink/mindlink/data/physionet/MNE-eegbci-data/`

---

## Download More Data

I've created a comprehensive download script for you!

### Quick Start

```bash
cd mindlink
python download_physionet_data.py
```

This will show you an interactive menu with options.

---

## Download Options

### Option 1: Single Subject (Testing)
**Best for**: Quick testing, learning
**Size**: ~4.5 MB
**Time**: 1-2 minutes

```bash
python download_physionet_data.py
# Choose option 1, enter subject number
```

### Option 2: 5 Subjects (Training)
**Best for**: Initial model training
**Size**: ~22 MB
**Time**: 5-10 minutes

```bash
python download_physionet_data.py
# Choose option 2
```

### Option 3: 10 Subjects (Better Performance)
**Best for**: Improved model accuracy
**Size**: ~45 MB
**Time**: 10-15 minutes

```bash
python download_physionet_data.py
# Choose option 3
```

### Option 4: 20 Subjects (Best Performance)
**Best for**: Production-ready model
**Size**: ~90 MB
**Time**: 20-30 minutes

```bash
python download_physionet_data.py
# Choose option 4
```

### Option 5: All 109 Subjects (Complete Dataset)
**Best for**: Research, maximum accuracy
**Size**: ~500 MB
**Time**: 1-2 hours

```bash
python download_physionet_data.py
# Choose option 5, confirm with "yes"
```

### Option 6: Check Downloaded Data
**Best for**: See what you already have

```bash
python download_physionet_data.py
# Choose option 6
```

---

## What Gets Downloaded

### Per Subject (3 files):
- `S001R04.edf` - Run 4: Left/Right fist imagery
- `S001R08.edf` - Run 8: Left/Right fist imagery  
- `S001R12.edf` - Run 12: Left/Right fist imagery

### File Details:
- **Format**: EDF (European Data Format)
- **Size**: ~1.5 MB per file
- **Channels**: 64 EEG channels
- **Sampling rate**: 160 Hz
- **Duration**: ~2 minutes per run
- **Trials**: ~45 per run

---

## Dataset Information

### PhysioNet EEGMMIDB
- **Full name**: EEG Motor Movement/Imagery Dataset
- **Source**: physionet.org
- **Subjects**: 109 volunteers (ages 21-64)
- **Tasks**: Motor imagery (imagine moving hands/feet)

### Motor Imagery Runs:
- **Run 4**: Left fist vs Right fist imagery
- **Run 8**: Left fist vs Right fist imagery
- **Run 12**: Left fist vs Right fist imagery

### Why These Runs?
Perfect for your drone control BCI:
- Left fist → Drone left
- Right fist → Drone right
- Both fists → Drone forward
- Rest → Drone backward

---

## Storage Location

Data is saved to:
```
mindlink/
└── mindlink/
    └── data/
        └── physionet/
            └── MNE-eegbci-data/
                └── files/
                    └── eegmmidb/
                        └── 1.0.0/
                            ├── S001/  (Subject 1)
                            │   ├── S001R04.edf
                            │   ├── S001R08.edf
                            │   └── S001R12.edf
                            ├── S002/  (Subject 2)
                            └── ...
```

---

## Using Downloaded Data

### Train on Single Subject:
```bash
python train_models.py  # Uses Subject 1 by default
```

### Train on Specific Subject:
```bash
python train_models.py 5  # Uses Subject 5
```

### Train on Multiple Subjects:
You'll need to modify `train_models.py` to loop through subjects, or I can create a batch training script for you.

---

## Recommendations

### For Your Project:

**Right Now (Learning Phase):**
- ✅ You already have Subject 1 (4.5 MB)
- ✅ This is enough for testing and learning
- ✅ Run the simulations and understand the pipeline

**Next Phase (Development):**
- 📥 Download 5-10 subjects (~22-45 MB)
- 🎯 Train on multiple subjects for better generalization
- 📊 Compare performance across subjects

**Production Phase (Before ITIE Hardware):**
- 📥 Download 20+ subjects (~90+ MB)
- 🎯 Train robust model that works across individuals
- 📊 Establish baseline performance metrics

**Research Phase (Optional):**
- 📥 Download all 109 subjects (~500 MB)
- 🎯 Maximum model performance
- 📊 Comprehensive analysis

---

## Benefits of More Data

| Subjects | Size | Training Time | Expected Accuracy | Use Case |
|----------|------|---------------|-------------------|----------|
| 1 | 4.5 MB | 30 sec | 55-65% | Testing, learning |
| 5 | 22 MB | 2-3 min | 60-70% | Initial training |
| 10 | 45 MB | 5-7 min | 65-75% | Good performance |
| 20 | 90 MB | 10-15 min | 70-80% | Production ready |
| 50 | 225 MB | 30-40 min | 75-85% | High performance |
| 109 | 500 MB | 1-2 hours | 80-90% | Maximum accuracy |

---

## Quick Commands

### Check what you have:
```bash
python download_physionet_data.py
# Choose option 6
```

### Download 5 subjects (recommended):
```bash
python download_physionet_data.py
# Choose option 2
```

### Train on downloaded data:
```bash
python train_models.py
```

---

## Troubleshooting

### "MNE not installed"
```bash
pip install mne
```

### "Download failed"
- Check internet connection
- Try again (MNE will resume from where it stopped)
- Try a different subject number

### "Not enough disk space"
- Check available space
- Download fewer subjects
- Clean up other files

### "Download is slow"
- PhysioNet servers can be slow
- Be patient, it will complete
- Downloads are cached (won't re-download)

---

## Summary

✅ **You already have**: Subject 1 (4.5 MB) - downloaded automatically
✅ **Recommended next**: Download 5-10 subjects for better training
✅ **Use the script**: `python download_physionet_data.py`
✅ **Interactive menu**: Easy to use, shows progress
✅ **Cached downloads**: Won't re-download existing data

Start with what you have, download more when you're ready to improve the model!
