"""Test full pipeline on a single YouTube download."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import torch
import soundfile as sf
import numpy as np

# Use a short song for quick test
TEST_URL = "https://www.youtube.com/watch?v=7wRHBLwpASw"  # Layla unplugged
WORK_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dataset', 'test_work')
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dataset', 'test_dl')
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

from dataset_prep.prepare_dataset import download_audio, extract_guitar_demucs, split_lead_rhythm

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Device: {device}')

# Step 1: Download
print('\n=== Step 1: Download ===')
audio_path = download_audio(TEST_URL, DOWNLOAD_DIR, 'test_song')
if not audio_path:
    print('Download failed')
    sys.exit(1)
print(f'Audio: {audio_path} ({os.path.getsize(audio_path)/1e6:.1f}MB)')

# Step 2: Demucs
print('\n=== Step 2: Demucs guitar extraction ===')
guitar_path = extract_guitar_demucs(audio_path, WORK_DIR, device)
print(f'Guitar: {guitar_path} ({os.path.getsize(guitar_path)/1e6:.1f}MB)')

# Step 3: V3+classifier
print('\n=== Step 3: V3+classifier lead/rhythm ===')
lead_path, rhythm_path = split_lead_rhythm(guitar_path, WORK_DIR)
print(f'Lead: {lead_path} ({os.path.getsize(lead_path)/1e6:.1f}MB)')
print(f'Rhythm: {rhythm_path} ({os.path.getsize(rhythm_path)/1e6:.1f}MB)')

print('\nPipeline test completed successfully!')
