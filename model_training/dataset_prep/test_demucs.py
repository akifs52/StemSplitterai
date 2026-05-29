"""Test demucs 6-stems extraction via Python API."""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import torch
import soundfile as sf
import numpy as np

# Load a short clip from an existing guitar stem for testing
sep = os.path.join(os.path.dirname(__file__), '..', '..', 'separated')
guitar_files = []
for root, dirs, files in os.walk(sep):
    for f in files:
        if f == 'guitar.wav':
            guitar_files.append(os.path.join(root, f))

if not guitar_files:
    print('No guitar stems found')
    sys.exit(1)

src = guitar_files[0]
print(f'Using: {src}')

# Take first 30 seconds for quick test
audio, sr = sf.read(src)
if audio.ndim == 1:
    audio = np.stack([audio, audio], axis=-1)
duration_sec = 30
n_samples = int(duration_sec * sr)
if audio.shape[0] > n_samples:
    audio = audio[:n_samples]

tmpdir = tempfile.mkdtemp()
test_path = os.path.join(tmpdir, 'test_30s.wav')
sf.write(test_path, audio, sr)
print(f'Wrote test file: {test_path} ({os.path.getsize(test_path)/1e6:.1f}MB)')

# Now load demucs model
from demucs import pretrained
from demucs.apply import apply_model
from demucs.audio import convert_audio

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Loading htdemucs_6s on {device}...')

model = pretrained.get_model('htdemucs_6s')
model.to(device)
model.eval()
print(f'Model loaded. Sample rate: {model.samplerate}')

# Load and process
audio_test, sr_test = sf.read(test_path)
if audio_test.ndim == 1:
    audio_test = np.stack([audio_test, audio_test], axis=0)
elif audio_test.shape[1] == 2:
    audio_test = audio_test.T

audio_t = torch.from_numpy(audio_test).float()

if sr_test != model.samplerate:
    from torchaudio.functional import resample
    audio_t = resample(audio_t, sr_test, model.samplerate)

audio_t = audio_t.unsqueeze(0).to(device)
print(f'Input shape: {audio_t.shape}')

with torch.no_grad():
    sources = apply_model(model, audio_t, device=device, shifts=1, split=True, overlap=0.25, progress=True)

print(f'Sources shape: {sources.shape}')
# htdemucs_6s: [batch, stems, channels, time] -> stems = [bass, drums, vocals, other, piano, guitar]
num_stems = sources.shape[1]
stem_names = model.sources
print(f'Stem names: {stem_names}')
print(f'Number of stems: {num_stems}')

# Extract guitar (last stem for htdemucs_6s)
guitar_idx = stem_names.index('guitar') if 'guitar' in stem_names else -1
print(f'Guitar index: {guitar_idx}')

if guitar_idx >= 0:
    guitar_source = sources[0, guitar_idx].cpu().numpy()
    print(f'Guitar shape: {guitar_source.shape}')
    out_path = os.path.join(tmpdir, 'extracted_guitar.wav')
    sf.write(out_path, guitar_source.T, model.samplerate)
    print(f'Saved guitar stem: {out_path} ({os.path.getsize(out_path)/1e6:.1f}MB)')

print('Demucs test completed successfully')
