"""Process babySlakh dataset for lead/rhythm guitar separation training.

Uses songs with 2+ guitar tracks:
- Maps lower-programnumber guitar -> lead_guitar
- Maps higher-programnumber guitar -> rhythm_guitar
- Creates Type 1 (MUSDB) format dataset

Also processes existing real-world guitar stems (app stems + any YouTube downloads)
using V3+classifier for bootstrap training.
"""
import sys, os, yaml
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import soundfile as sf
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BABY_SLAKH_DIR = os.path.join(BASE_DIR, 'dataset', 'babyslakh_16k')
DATASET_DIR = os.path.join(BASE_DIR, 'dataset')
SAMPLE_RATE = 44100  # Target sample rate (upsample from 16kHz)

# GM program numbers for guitar family
GUITAR_PROGRAMS = set(range(24, 32))

# Classification: lead vs rhythm based on program number
# Lead: clean, jazz, nylon, steel (lighter timbres) 
# Rhythm: overdriven, distortion, muted (heavier/thicker)
LEAD_PROGRAMS = {24, 25, 26, 27, 28, 31}  # Nylon, Steel, Jazz, Clean, Muted, Harmonics
RHYTHM_PROGRAMS = {29, 30}  # Overdriven, Distortion


def get_guitar_tracks(track_dir):
    """Get list of (stem_id, program_num, wav_path) for guitar stems."""
    metadata_path = os.path.join(track_dir, 'metadata.yaml')
    if not os.path.exists(metadata_path):
        return []
    
    with open(metadata_path, 'r') as f:
        meta = yaml.safe_load(f)
    
    stems = meta.get('stems', {})
    guitar_tracks = []
    
    for stem_id, stem_info in stems.items():
        inst_class = stem_info.get('inst_class', '')
        program_num = stem_info.get('program_num', -1)
        
        if inst_class.lower() == 'guitar' or program_num in GUITAR_PROGRAMS:
            stem_path = os.path.join(track_dir, 'stems', f'{stem_id}.wav')
            if os.path.exists(stem_path):
                guitar_tracks.append((stem_id, program_num, stem_path))
    
    return guitar_tracks


def classify_lead_rhythm(tracks):
    """Classify guitar tracks as lead or rhythm.
    
    Strategy:
    - If 2 tracks: assign lead (cleaner/lower) and rhythm (heavier)
    - If 3+ tracks: take cleanest as lead, heaviest as rhythm
    """
    if len(tracks) < 2:
        return None, None
    
    # Sort by program number (24=nylon clean, 30=distorted heavy)
    tracks_sorted = sorted(tracks, key=lambda t: t[1])
    
    lead_idx = 0
    rhythm_idx = -1
    
    # For 2 tracks, first is lead, last is rhythm
    # For 3+, pick two most contrasting
    if len(tracks) >= 2:
        # Pick the two that differ most in program number
        best_pair = None
        best_diff = -1
        for i in range(len(tracks)):
            for j in range(i+1, len(tracks)):
                diff = abs(tracks[i][1] - tracks[j][1])
                if diff > best_diff:
                    best_diff = diff
                    best_pair = (i, j)
        
        if best_pair:
            i, j = best_pair
            # Lower program num -> lead, higher -> rhythm
            if tracks[i][1] <= tracks[j][1]:
                lead_idx, rhythm_idx = i, j
            else:
                lead_idx, rhythm_idx = j, i
    
    lead = tracks[lead_idx]
    rhythm = tracks[rhythm_idx]
    
    return lead, rhythm


def upsample_to_44100(audio, orig_sr=16000, target_sr=44100):
    """Upsample audio from 16kHz to 44.1kHz."""
    if orig_sr == target_sr:
        return audio
    from torchaudio.functional import resample
    import torch
    audio_t = torch.from_numpy(audio).float()
    if audio_t.ndim == 1:
        audio_t = audio_t.unsqueeze(0)
    elif audio_t.shape[0] > 2:
        audio_t = audio_t.T
    audio_t = resample(audio_t, orig_sr, target_sr)
    return audio_t.numpy().T if audio_t.shape[0] <= 2 else audio_t.numpy()


def process_babyslakh():
    """Process babySlakh: find songs with 2+ guitar tracks, create dataset."""
    songs = sorted(os.listdir(BABY_SLAKH_DIR))
    
    train_dir = os.path.join(DATASET_DIR, 'train')
    valid_dir = os.path.join(DATASET_DIR, 'valid')
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(valid_dir, exist_ok=True)
    
    dataset_counts = {'train': 0, 'valid': 0}
    skipped = 0
    
    for i, song_id in enumerate(tqdm(songs, desc='Processing babySlakh')):
        track_dir = os.path.join(BABY_SLAKH_DIR, song_id, 'stems')
        if not os.path.isdir(os.path.join(BABY_SLAKH_DIR, song_id)):
            continue
        
        guitars = get_guitar_tracks(os.path.join(BABY_SLAKH_DIR, song_id))
        
        if len(guitars) < 2:
            skipped += 1
            continue
        
        lead, rhythm = classify_lead_rhythm(guitars)
        if lead is None or rhythm is None:
            skipped += 1
            continue
        
        # Load audio files (16kHz mono)
        try:
            lead_audio, sr = sf.read(lead[2])
            rhythm_audio, _ = sf.read(rhythm[2])
        except Exception as e:
            print(f'  Error loading {song_id}: {e}')
            skipped += 1
            continue
        
        # Both should be mono at 16kHz
        if lead_audio.ndim > 1:
            lead_audio = lead_audio.mean(axis=1)
        if rhythm_audio.ndim > 1:
            rhythm_audio = rhythm_audio.mean(axis=1)
        
        # Ensure same length
        min_len = min(len(lead_audio), len(rhythm_audio))
        lead_audio = lead_audio[:min_len]
        rhythm_audio = rhythm_audio[:min_len]
        
        # Create mixture
        mixture = lead_audio + rhythm_audio
        
        # Upsample to 44.1kHz
        if sr != SAMPLE_RATE:
            lead_audio = upsample_to_44100(lead_audio, sr, SAMPLE_RATE)
            rhythm_audio = upsample_to_44100(rhythm_audio, sr, SAMPLE_RATE)
            mixture = upsample_to_44100(mixture, sr, SAMPLE_RATE)
        
        # Convert to stereo (mono -> dual mono)
        def to_stereo(mono):
            return np.column_stack([mono, mono])
        
        # Normalize
        peak = max(np.abs(mixture).max(), 1e-8)
        mixture = np.clip(mixture / peak * 0.95, -1.0, 1.0)
        lead_audio = np.clip(lead_audio / peak * 0.95, -1.0, 1.0)
        rhythm_audio = np.clip(rhythm_audio / peak * 0.95, -1.0, 1.0)
        
        # First 80% train, last 20% valid
        is_valid = (i % 5 == 0)  # 20% for validation
        
        song_name = f'slakh_{song_id}'
        song_dir = os.path.join(valid_dir if is_valid else train_dir, song_name)
        os.makedirs(song_dir, exist_ok=True)
        
        sf.write(os.path.join(song_dir, 'mixture.wav'), to_stereo(mixture), SAMPLE_RATE)
        sf.write(os.path.join(song_dir, 'lead_guitar.wav'), to_stereo(lead_audio), SAMPLE_RATE)
        sf.write(os.path.join(song_dir, 'rhythm_guitar.wav'), to_stereo(rhythm_audio), SAMPLE_RATE)
        
        dataset_counts['valid' if is_valid else 'train'] += 1
    
    print(f'\nDataset created:')
    print(f'  Train: {dataset_counts["train"]} songs')
    print(f'  Valid: {dataset_counts["valid"]} songs')
    print(f'  Skipped (0-1 guitar): {skipped}')


def add_bootstrap_stems():
    """Add existing guitar stems processed through V3+classifier."""
    train_dir = os.path.join(DATASET_DIR, 'train')
    valid_dir = os.path.join(DATASET_DIR, 'valid')
    
    # Find existing guitar stems
    from backend.guitar_splitter import split_guitar
    
    app_sep = os.path.join(os.path.dirname(__file__), '..', '..', 'separated')
    guitar_files = []
    for root, dirs, files in os.walk(app_sep):
        for f in files:
            if f == 'guitar.wav':
                guitar_files.append(os.path.join(root, f))
    
    # Also find real-world downloads
    dl_dir = os.path.join(DATASET_DIR, 'downloads')
    if os.path.isdir(dl_dir):
        for f in os.listdir(dl_dir):
            if f.endswith('.wav') and f != 'sweet_child.wav':
                guitar_files.append(os.path.join(dl_dir, f))
    
    for i, guitar_path in enumerate(tqdm(guitar_files, desc='Processing bootstrap stems')):
        song_name = f'real_{i:03d}'
        song_dir = os.path.join(train_dir, song_name)
        if os.path.exists(os.path.join(song_dir, 'mixture.wav')):
            continue
        
        try:
            result = split_guitar(guitar_path)
            
            lead_path = rhythm_path = None
            for item in result:
                if item['name'] == 'lead_guitar':
                    lead_path = item['path']
                elif item['name'] == 'rhythm_guitar':
                    rhythm_path = item['path']
            
            if not lead_path or not rhythm_path:
                continue
            
            os.makedirs(song_dir, exist_ok=True)
            # Copy mixture (original guitar stem)
            import shutil
            shutil.copy2(guitar_path, os.path.join(song_dir, 'mixture.wav'))
            shutil.copy2(lead_path, os.path.join(song_dir, 'lead_guitar.wav'))
            shutil.copy2(rhythm_path, os.path.join(song_dir, 'rhythm_guitar.wav'))
        except Exception as e:
            print(f'  Error processing {guitar_path}: {e}')
            continue


if __name__ == '__main__':
    process_babyslakh()
    print('\n=== Adding bootstrap stems ===')
    add_bootstrap_stems()
    print('\nDone!')
