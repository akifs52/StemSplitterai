import os, sys, io, yaml, gzip, tarfile, requests, time
import numpy as np
from tqdm import tqdm

# MIDI guitar programs: 24-31
GUITAR_PROGRAMS = set(range(24, 32))
OUTPUT_DIR = 'D:/qt/stemsplitteraiapp/dataset/slakh2100_guitar_raw'
TAR_PREFIX = 'slakh2100_flac_redux/'
URL = 'https://zenodo.org/records/4599666/files/slakh2100_flac_redux.tar.gz?download=1'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def is_guitar_stem(stem_info):
    prog = stem_info.get('program_num', -1)
    cls = stem_info.get('inst_class', '')
    return prog in GUITAR_PROGRAMS or cls.lower() == 'guitar'

def build_guitar_stems(data):
    meta = yaml.safe_load(data)
    stems = meta.get('stems', {})
    return sorted(sname for sname, sinfo in stems.items() if is_guitar_stem(sinfo))

def save_file(rel_path, data):
    out = os.path.join(OUTPUT_DIR, rel_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as fh:
        fh.write(data)

# Check existing progress: tracks that already have metadata saved
existing_tracks = set()
if os.path.exists(OUTPUT_DIR):
    for d in os.listdir(OUTPUT_DIR):
        meta_path = os.path.join(OUTPUT_DIR, d, 'metadata.yaml')
        if os.path.isfile(meta_path):
            existing_tracks.add(d)
if existing_tracks:
    print(f'Resuming: {len(existing_tracks)} tracks already extracted, skipping them')

# Download with streaming
print(f'Downloading from Zenodo...')
resp = requests.get(URL, stream=True, timeout=30)
resp.raise_for_status()

total_size = int(resp.headers.get('content-length', 0))
print(f'Total download size: {total_size/1e9:.1f} GB')

# Progress tracking
class ProgressReader:
    def __init__(self, raw, total):
        self.raw = raw
        self.total = total
        self.read_bytes = 0
        self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc='Downloading')
    def read(self, size=-1):
        data = self.raw.read(size)
        if data:
            self.read_bytes += len(data)
            self.pbar.update(len(data))
        return data
    def close(self):
        self.pbar.close()

raw_progress = ProgressReader(resp.raw, total_size)
tar = tarfile.open(fileobj=raw_progress, mode='r|gz')

# State
last_track = None
track_buffers = []  # list of (rel_path, data) for current track
track_guitar_stems = {}  # cache
total_extracted = 0
total_guitar_tracks = len(existing_tracks)
total_tracks = 0
start_time = time.time()

for member in tar:
    fname = member.name
    if not fname.startswith(TAR_PREFIX):
        continue
    
    rel_path = fname[len(TAR_PREFIX):]
    parts = rel_path.split('/')
    track_name = parts[0] if parts else ''
    
    if not track_name or not track_name.startswith('Track'):
        continue
    
    # Track transition → flush previous buffer
    if track_name != last_track:
        # Discard buffer from previous unknown track (no guitar)
        track_buffers = []
        last_track = track_name
    
    # Skip already-extracted tracks
    if track_name in existing_tracks:
        continue
    
    is_meta = rel_path.endswith('metadata.yaml')
    is_mix = rel_path.endswith('mix.flac')
    is_stem = '/stems/' in rel_path and rel_path.endswith('.flac')
    
    if not (is_meta or is_mix or is_stem):
        continue
    
    f = tar.extractfile(member)
    if f is None:
        continue
    data = f.read()
    
    if is_meta:
        total_tracks += 1
        guitar_stems = build_guitar_stems(data)
        track_guitar_stems[track_name] = guitar_stems
        
        if guitar_stems:
            total_guitar_tracks += 1
            # Save metadata
            save_file(rel_path, data)
            # Save all buffered files for this track
            for buf_rel, buf_data in track_buffers:
                # For stems, only save if it's a guitar stem
                if '/stems/' in buf_rel:
                    stem_name = buf_rel.split('/')[-1].replace('.flac', '')
                    if stem_name not in guitar_stems:
                        continue
                save_file(buf_rel, buf_data)
                total_extracted += 1
            track_buffers = []
        else:
            # No guitar in this track, discard buffer
            track_buffers = []
            
    elif is_mix:
        if track_name in track_guitar_stems:
            if track_guitar_stems[track_name]:
                save_file(rel_path, data)
                total_extracted += 1
        else:
            track_buffers.append((rel_path, data))
            
    elif is_stem:
        stem_name = parts[-1].replace('.flac', '') if len(parts) >= 4 else ''
        if track_name in track_guitar_stems:
            if stem_name in track_guitar_stems[track_name]:
                save_file(rel_path, data)
                total_extracted += 1
        else:
            track_buffers.append((rel_path, data))
    
    if total_tracks % 200 == 0 and total_tracks > 0:
        elapsed = time.time() - start_time
        speed = raw_progress.read_bytes / elapsed / 1e6 if elapsed > 0 else 0
        tqdm.write(f'[Progress] Tracks: {total_tracks}, Guitar: {total_guitar_tracks}, '
                   f'Extracted: {total_extracted} files, Speed: {speed:.1f} MB/s')

raw_progress.close()
tar.close()

elapsed_h = (time.time() - start_time) / 3600
print(f'\nDone! {elapsed_h:.1f} hours')
print(f'Tracks processed: {total_tracks + len(existing_tracks)}')
print(f'Tracks with guitar: {total_guitar_tracks}')
print(f'Files extracted: {total_extracted}')
print(f'Output: {OUTPUT_DIR}')
