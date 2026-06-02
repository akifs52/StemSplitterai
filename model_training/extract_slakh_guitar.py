import os, sys, yaml, zipfile, time
import soundfile as sf
import numpy as np
from tqdm import tqdm

INPUT_ZIP = 'D:/qt/stemsplitteraiapp/dataset/Slakh2100.zip'
OUTPUT_DIR = 'D:/qt/stemsplitteraiapp/dataset/slakh2100_guitar_raw'
PREFIX = 'slakh2100_flac_redux/'
GUITAR_PROGRAMS = set(range(24, 32))

print(f'Opening {INPUT_ZIP}...')
z = zipfile.ZipFile(INPUT_ZIP, 'r')
names = z.namelist()
zip_size = os.path.getsize(INPUT_ZIP)
print(f'Total zip entries: {len(names)} ({zip_size/1e9:.1f} GB)')

# Skip slakh2100_flac_redux/ prefix and omitted/test splits
track_names = set()
for name in names:
    rel = name.removeprefix(PREFIX)
    parts = rel.split('/')
    if parts[0] in ('omitted', 'test', 'README'):
        continue
    if parts[0] in ('train', 'validation'):
        if len(parts) >= 2 and parts[1].startswith('Track'):
            track_names.add(parts[1])
    elif parts[0].startswith('Track'):
        track_names.add(parts[0])

print(f'Tracks to process (train+validation, excluded omitted/test): {len(track_names)}')

# Pass 1: Read all metadata.yaml first (tiny files, fast)
# This avoids buffering audio data
print('Pass 1: Scanning metadata to identify guitar stems...')
track_guitar_stems = {}
for name in tqdm(names, desc='Scanning'):
    rel = name.removeprefix(PREFIX)
    parts = rel.split('/')
    if parts[0] in ('omitted', 'test', 'README'):
        continue
    if not rel.endswith('metadata.yaml'):
        continue
    data = z.read(name)
    meta = yaml.safe_load(data)
    stems = meta.get('stems', {})
    guitar = [s for s, info in stems.items()
              if info.get('program_num', -1) in GUITAR_PROGRAMS
              or info.get('inst_class', '').lower() == 'guitar']
    if guitar:
        track = parts[1] if parts[0] in ('train', 'validation') else parts[0]
        track_guitar_stems[track] = guitar

print(f'Tracks with guitar stems: {len(track_guitar_stems)}')

# Pass 2: Extract only guitar-related files
print('Pass 2: Extracting files...')
extracted = 0
total_to_extract = 0
for stems in track_guitar_stems.values():
    total_to_extract += len(stems) + 2  # stems + mix + metadata

for name in tqdm(names, desc='Extracting'):
    rel = name.removeprefix(PREFIX)
    parts = rel.split('/')
    if parts[0] in ('omitted', 'test', 'README'):
        continue
    if rel == '':
        continue
    if rel.endswith('.mid'):
        continue
    if rel == 'all_src.mid':
        continue

    track = parts[1] if parts[0] in ('train', 'validation') else parts[0]
    if not track.startswith('Track'):
        continue
    if track not in track_guitar_stems:
        continue

    if rel.endswith('metadata.yaml') or rel.endswith('mix.flac'):
        out = os.path.join(OUTPUT_DIR, track, os.path.basename(rel))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as f:
            f.write(z.read(name))
        extracted += 1
    elif '/stems/' in rel and rel.endswith('.flac'):
        stem_name = rel.split('/')[-1].replace('.flac', '')
        if stem_name in track_guitar_stems[track]:
            out = os.path.join(OUTPUT_DIR, track, 'stems', f'{stem_name}.flac')
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, 'wb') as f:
                f.write(z.read(name))
            extracted += 1

z.close()
print(f'\nDone! Extracted {extracted} files for {len(track_guitar_stems)} tracks.')
print(f'Output: {OUTPUT_DIR}')
