"""
PhysioNet EEGMMIDB Data Downloader
Downloads motor imagery EEG data for training the MindLink BCI system.

This script downloads the PhysioNet EEG Motor Movement/Imagery Dataset (EEGMMIDB)
which contains 109 subjects performing motor imagery tasks.

Dataset Info:
- 64 EEG channels (10-10 system)
- 160 Hz sampling rate
- Motor imagery tasks: left fist, right fist, both fists, both feet
- Runs 4, 8, 12 contain motor imagery data
"""

import os
import sys
from pathlib import Path

try:
    import mne
    from mne.datasets import eegbci
    MNE_AVAILABLE = True
except ImportError:
    print("ERROR: MNE not installed. Install with: pip install mne")
    sys.exit(1)


def download_subject(subject_id: int, runs: list = None, data_path: str = "mindlink/data/physionet/"):
    """
    Download PhysioNet EEGMMIDB data for a specific subject.
    
    Args:
        subject_id: Subject number (1-109)
        runs: List of run numbers to download (default: [4, 8, 12] for motor imagery)
        data_path: Where to save the data
    
    Returns:
        List of downloaded file paths
    """
    if runs is None:
        runs = [4, 8, 12]  # Motor imagery runs
    
    print(f"\n{'='*70}")
    print(f"Downloading Subject {subject_id}")
    print(f"{'='*70}")
    print(f"Runs: {runs}")
    print(f"Path: {data_path}")
    
    try:
        # Download using MNE
        raw_files = eegbci.load_data(subject_id, runs, path=data_path)
        
        print(f"\n✓ Downloaded {len(raw_files)} files for Subject {subject_id}")
        for f in raw_files:
            file_size = os.path.getsize(f) / (1024 * 1024)  # MB
            print(f"  - {Path(f).name} ({file_size:.2f} MB)")
        
        return raw_files
    
    except Exception as e:
        print(f"\n✗ Error downloading Subject {subject_id}: {e}")
        return []


def download_multiple_subjects(subject_ids: list, runs: list = None, data_path: str = "mindlink/data/physionet/"):
    """
    Download data for multiple subjects.
    
    Args:
        subject_ids: List of subject numbers (1-109)
        runs: List of run numbers (default: [4, 8, 12])
        data_path: Where to save the data
    """
    if runs is None:
        runs = [4, 8, 12]
    
    print(f"\n{'='*70}")
    print(f"PHYSIONET EEGMMIDB BATCH DOWNLOAD")
    print(f"{'='*70}")
    print(f"Subjects: {len(subject_ids)} ({min(subject_ids)} to {max(subject_ids)})")
    print(f"Runs per subject: {runs}")
    print(f"Total files: {len(subject_ids) * len(runs)}")
    print(f"Estimated size: ~{len(subject_ids) * len(runs) * 1.5:.0f} MB")
    print(f"{'='*70}\n")
    
    downloaded = []
    failed = []
    
    for i, subject_id in enumerate(subject_ids, 1):
        print(f"\n[{i}/{len(subject_ids)}] Processing Subject {subject_id}...")
        
        files = download_subject(subject_id, runs, data_path)
        
        if files:
            downloaded.append(subject_id)
        else:
            failed.append(subject_id)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*70}")
    print(f"✓ Successfully downloaded: {len(downloaded)} subjects")
    if failed:
        print(f"✗ Failed: {len(failed)} subjects - {failed}")
    print(f"{'='*70}\n")
    
    return downloaded, failed


def get_dataset_info():
    """Print information about the PhysioNet EEGMMIDB dataset."""
    print(f"\n{'='*70}")
    print("PHYSIONET EEGMMIDB DATASET INFORMATION")
    print(f"{'='*70}")
    print("""
Dataset: EEG Motor Movement/Imagery Dataset
Source: PhysioNet (physionet.org)
Subjects: 109 volunteers
Age range: 21-64 years

Recording Setup:
- Channels: 64 EEG (10-10 system)
- Sampling rate: 160 Hz
- Reference: Linked mastoids
- Ground: Forehead

Tasks (14 runs per subject):
- Run 1: Baseline, eyes open
- Run 2: Baseline, eyes closed
- Run 3: Task 1 (open/close left or right fist)
- Run 4: Task 2 (imagine opening/closing left or right fist) ← MOTOR IMAGERY
- Run 5: Task 3 (open/close both fists or both feet)
- Run 6: Task 4 (imagine opening/closing both fists or both feet)
- Run 7: Task 1
- Run 8: Task 2 (imagine opening/closing left or right fist) ← MOTOR IMAGERY
- Run 9: Task 3
- Run 10: Task 4
- Run 11: Task 1
- Run 12: Task 2 (imagine opening/closing left or right fist) ← MOTOR IMAGERY
- Run 13: Task 3
- Run 14: Task 4

Motor Imagery Runs (for BCI):
- Runs 4, 8, 12: Left fist vs Right fist imagery
- Runs 6, 10, 14: Both fists vs Both feet imagery

For MindLink Project:
- We use Runs 4, 8, 12 (left/right fist imagery)
- These map to drone control: Left, Right, Forward, Backward
- Each run: ~2 minutes, ~45 trials

File Format:
- EDF (European Data Format)
- ~1.5 MB per run
- ~4.5 MB per subject (3 runs)
    """)
    print(f"{'='*70}\n")


def check_downloaded_data(data_path: str = "mindlink/data/physionet/"):
    """Check what data has already been downloaded."""
    print(f"\n{'='*70}")
    print("CHECKING DOWNLOADED DATA")
    print(f"{'='*70}")
    
    base_path = Path(data_path) / "MNE-eegbci-data/files/eegmmidb/1.0.0"
    
    if not base_path.exists():
        print(f"No data found at: {base_path}")
        print("Run download to get data.")
        return []
    
    subjects = []
    total_size = 0
    
    for subject_dir in sorted(base_path.glob("S*")):
        subject_num = int(subject_dir.name[1:])
        edf_files = list(subject_dir.glob("*.edf"))
        
        if edf_files:
            subjects.append(subject_num)
            size = sum(f.stat().st_size for f in edf_files) / (1024 * 1024)
            total_size += size
            print(f"✓ Subject {subject_num:3d}: {len(edf_files)} files ({size:.2f} MB)")
    
    print(f"\n{'='*70}")
    print(f"Total: {len(subjects)} subjects, {total_size:.2f} MB")
    print(f"{'='*70}\n")
    
    return subjects


def main():
    """Main download interface."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         PhysioNet EEGMMIDB Data Downloader for MindLink         ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Show dataset info
    get_dataset_info()
    
    # Check existing data
    existing = check_downloaded_data()
    
    # Download options
    print("\nDOWNLOAD OPTIONS:")
    print("="*70)
    print("1. Download single subject (recommended for testing)")
    print("2. Download 5 subjects (good for training)")
    print("3. Download 10 subjects (better performance)")
    print("4. Download 20 subjects (best performance)")
    print("5. Download all 109 subjects (complete dataset, ~500 MB)")
    print("6. Check downloaded data only (no download)")
    print("0. Exit")
    print("="*70)
    
    try:
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == "0":
            print("Exiting...")
            return
        
        elif choice == "1":
            subject = input("Enter subject number (1-109) [default: 1]: ").strip()
            subject = int(subject) if subject else 1
            download_subject(subject)
        
        elif choice == "2":
            print("\nDownloading subjects 1-5...")
            download_multiple_subjects(list(range(1, 6)))
        
        elif choice == "3":
            print("\nDownloading subjects 1-10...")
            download_multiple_subjects(list(range(1, 11)))
        
        elif choice == "4":
            print("\nDownloading subjects 1-20...")
            download_multiple_subjects(list(range(1, 21)))
        
        elif choice == "5":
            confirm = input("\nDownload all 109 subjects (~500 MB)? This will take time. (yes/no): ").strip().lower()
            if confirm == "yes":
                print("\nDownloading all subjects...")
                download_multiple_subjects(list(range(1, 110)))
            else:
                print("Cancelled.")
        
        elif choice == "6":
            check_downloaded_data()
        
        else:
            print("Invalid choice.")
    
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\n✓ Done!\n")


if __name__ == "__main__":
    main()
