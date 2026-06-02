import os, sys, yaml
import soundfile as sf
import numpy as np
from tqdm import tqdm

RAW_DIR = 'D:/qt/stemsplitteraiapp/dataset/slakh2100_guitar_raw'
TRAIN_DIR = 'D:/qt/stemsplitteraiapp/dataset/train_slakh'
VALID_DIR = 'D:/qt/stemsplitteraiapp/dataset/valid_slakh'

# Read split info
split_map = {}  # track_name -> 'train' or 'validation'
with open(os.path.join(RAW_DIR, 'split_info.txt')) as f:
    for line in f:
        track, split = line.strip().split()
        split_map[track] = split

def mono_to_stereo(mono_data):
    return np.stack([mono_data, mono_data], axis=0)

SKIP_EXISTING = True

def process_track(track_dir, track_name, split):
    meta_path = os.path.join(track_dir, 'metadata.yaml')
    if not os.path.isfile(meta_path):
        return False
    
    with open(meta_path) as f:
        meta = yaml.safe_load(f)
    
    stems_info = meta.get('stems', {})
    guitar_stems = [s for s, info in stems_info.items()
                    if info.get('program_num', -1) in range(24, 32)
                    or info.get('inst_class', '').lower() == 'guitar']
    
    if not guitar_stems:
        return False
    
    # Read mix
    mix_path = os.path.join(track_dir, 'mix.flac')
    if not os.path.isfile(mix_path):
        return False
    mix, sr = sf.read(mix_path)
    mix_stereo = mono_to_stereo(mix)
    
    # Read each guitar stem and calculate RMS energy
    stems_audio = {}
    for stem_name in guitar_stems:
        stem_path = os.path.join(track_dir, 'stems', f'{stem_name}.flac')
        if not os.path.isfile(stem_path):
            continue
        data, _ = sf.read(stem_path)
        rms = np.sqrt(np.mean(data**2))
        stems_audio[stem_name] = (data, rms)
    
    if not stems_audio:
        return False
    
    # Assign lead = highest RMS, rhythm = sum of rest
    sorted_stems = sorted(stems_audio.items(), key=lambda x: -x[1][1])
    lead_name, (lead_data, _) = sorted_stems[0]
    
    if len(sorted_stems) == 1:
        rhythm_data = np.zeros_like(lead_data)
    else:
        rhythm_data = sum(data for name, (data, _) in sorted_stems[1:])
    
    # Normalize to prevent clipping (match mix peak)
    max_peak = max(np.abs(mix).max(), np.abs(lead_data).max(), np.abs(rhythm_data).max())
    if max_peak > 0.95:
        scale = 0.95 / max_peak
        lead_data *= scale
        rhythm_data *= scale
    
    # Convert to stereo
    lead_stereo = mono_to_stereo(lead_data)
    rhythm_stereo = mono_to_stereo(rhythm_data)
    
    # Output path
    out_base = TRAIN_DIR if split == 'train' else VALID_DIR
    out_dir = os.path.join(out_base, track_name)
    os.makedirs(out_dir, exist_ok=True)
    
    sf.write(os.path.join(out_dir, 'mixture.flac'), mix_stereo.T, sr)
    sf.write(os.path.join(out_dir, 'lead_guitar.flac'), lead_stereo.T, sr)
    sf.write(os.path.join(out_dir, 'rhythm_guitar.flac'), rhythm_stereo.T, sr)
    
    return True

# Process tracks
processed = 0
total_tracks = 0

track_dirs = [d for d in os.listdir(RAW_DIR) if d.startswith('Track') and os.path.isdir(os.path.join(RAW_DIR, d))]
print(f'Found {len(track_dirs)} track directories')

for track_name in tqdm(sorted(track_dirs)):
    if track_name not in split_map:
        continue
    track_dir = os.path.join(RAW_DIR, track_name)
    split = split_map[track_name]
    
    out_base = TRAIN_DIR if split == 'train' else VALID_DIR
    out_dir = os.path.join(out_base, track_name)
    
    # Skip if already processed
    if SKIP_EXISTING and os.path.isdir(out_dir) and os.path.isfile(os.path.join(out_dir, 'mixture.flac')):
        total_tracks += 1
        processed += 1
        continue
    
    if process_track(track_dir, track_name, split):
        processed += 1
    total_tracks += 1

# Count output files
train_count = len(os.listdir(TRAIN_DIR)) if os.path.exists(TRAIN_DIR) else 0
valid_count = len(os.listdir(VALID_DIR)) if os.path.exists(VALID_DIR) else 0

print(f'\nDone! Processed {processed}/{total_tracks} tracks')
print(f'Train tracks: {train_count}')
print(f'Valid tracks: {valid_count}')
