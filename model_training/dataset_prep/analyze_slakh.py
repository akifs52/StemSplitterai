"""Analyze babySlakh dataset for multi-guitar tracks."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mirdata.datasets import slakh

dataset = slakh.Dataset(data_home='../../dataset/slakh')
mtracks = dataset.load_multitracks()
print(f'Total multitracks: {len(mtracks)}')

# Inspect first track structure
first_id = list(mtracks.keys())[0]
first_mt = mtracks[first_id]
print(f'\nFirst track ID: {first_id}')
track_ids = list(first_mt.tracks.keys())
print(f'Number of instrument tracks: {len(track_ids)}')
print(f'First 5 track IDs: {track_ids[:5]}')

# Get first track's attributes
first_track = first_mt.tracks[track_ids[0]]
track_attrs = [a for a in dir(first_track) if not a.startswith('_')]
print(f'Track attributes: {track_attrs}')

if hasattr(first_track, 'program_number'):
    print(f'First track program_number: {first_track.program_number}')
    print(f'First track instrument: {first_track.instrument}')

# Now analyze all tracks
guitar_progs = list(range(24, 32))
multi_guitar = []
for tid, mt in mtracks.items():
    guitar_tracks = []
    for track_id, track in mt.tracks.items():
        if hasattr(track, 'program_number') and track.program_number in guitar_progs:
            guitar_tracks.append((track_id, track.program_number))
        elif hasattr(track, 'instrument'):
            inst = track.instrument.lower() if track.instrument else ''
            if 'guitar' in inst:
                guitar_tracks.append((track_id, -1))
    if len(guitar_tracks) >= 2:
        multi_guitar.append((tid, len(guitar_tracks), guitar_tracks))

print(f'\nSongs with 2+ guitar tracks: {len(multi_guitar)}')

prog_names = {24:'Nylon', 25:'Steel_Acoustic', 26:'Jazz', 27:'Clean', 28:'Muted', 29:'Overdriven', 30:'Distortion', 31:'Harmonics'}
for tid, count, tracks in multi_guitar[:20]:
    desc = []
    for t_id, prog in tracks:
        name = prog_names.get(prog, f'GM{prog}')
        desc.append(f'{t_id[:20]}...={name}')
    print(f'  {tid}: {count} tracks -> {desc}')

if len(multi_guitar) > 20:
    print(f'  ... and {len(multi_guitar)-20} more')

# Also count songs with 1 guitar track (for bootstrap)
one_guitar = sum(1 for _, c, _ in multi_guitar if c == 1)
print(f'\nSongs with exactly 1 guitar: {one_guitar}')
print(f'Songs with 3+ guitars: {sum(1 for _, c, _ in multi_guitar if c >= 3)}')
