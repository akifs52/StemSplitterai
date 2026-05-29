import os
import sys
import subprocess
import argparse
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import torch
import soundfile as sf
import numpy as np
from tqdm import tqdm


def download_audio(url, output_dir, song_name=None):
    """Download audio from YouTube using yt-dlp (best quality, stereo)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / '%(title)s_%(id)s.%(ext)s')
    cmd = [
        'yt-dlp', '-x', '--audio-format', 'wav', '--audio-quality', '0',
        '-o', output_template, url,
        '--no-playlist',
        '--extract-audio',
    ]
    if song_name:
        cmd.extend(['--output', str(output_dir / f'{song_name}.%(ext)s')])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")
    
    # Find the downloaded file (most recently modified)
    wav_files = sorted(list(output_dir.glob('*.wav')), key=os.path.getmtime, reverse=True)
    if not wav_files:
        ogg_files = sorted(list(output_dir.glob('*.ogg')), key=os.path.getmtime, reverse=True)
        m4a_files = sorted(list(output_dir.glob('*.m4a')), key=os.path.getmtime, reverse=True)
        mp3_files = sorted(list(output_dir.glob('*.mp3')), key=os.path.getmtime, reverse=True)
        all_audio = wav_files + ogg_files + m4a_files + mp3_files
        if not all_audio:
            return None
        return str(all_audio[0])
    return str(wav_files[0])


def extract_guitar_demucs(audio_path, output_dir, device='cuda'):
    """Extract guitar stem using demucs 6-stems model."""
    from demucs import pretrained
    from demucs.apply import apply_model
    from demucs.audio import convert_audio
    
    output_dir = os.path.join(output_dir, 'demucs_guitar')
    os.makedirs(output_dir, exist_ok=True)
    
    song_basename = os.path.splitext(os.path.basename(audio_path))[0]
    guitar_path = os.path.join(output_dir, f'{song_basename}_guitar.wav')
    
    if os.path.exists(guitar_path):
        return guitar_path
    
    # Load model
    model = pretrained.get_model('htdemucs_6s')
    model.to(device)
    model.eval()
    
    # Load audio
    audio, sr = sf.read(audio_path)
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=0)
    elif audio.shape[1] == 2:
        audio = audio.T
    audio_t = torch.from_numpy(audio).float()
    
    # Convert to model sample rate
    if sr != model.samplerate:
        from torchaudio.functional import resample
        audio_t = resample(audio_t, sr, model.samplerate)
    
    audio_t = audio_t.unsqueeze(0).to(device)
    
    # Apply model
    with torch.no_grad():
        sources = apply_model(model, audio_t, device=device, shifts=1, split=True, overlap=0.25, progress=True)
    
    # Find guitar stem index dynamically
    stem_names = model.sources
    guitar_idx = stem_names.index('guitar') if 'guitar' in stem_names else -1
    if guitar_idx < 0:
        raise RuntimeError(f"Model sources {stem_names} don't contain 'guitar'")
    guitar_source = sources[0, guitar_idx].cpu().numpy()
    
    # Save guitar stem
    sf.write(guitar_path, guitar_source.T, model.samplerate)
    
    return guitar_path


def split_lead_rhythm(guitar_path, output_dir):
    """Split guitar stem into lead and rhythm using V3+classifier."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from backend.guitar_splitter import split_guitar
    
    # split_guitar writes output files in the same dir as input
    # with suffixes _lead_guitar.wav and _rhythm_guitar.wav
    
    # Copy guitar to work dir first so output files go there
    import shutil
    work_guitar_path = os.path.join(output_dir, os.path.basename(guitar_path))
    shutil.copy2(guitar_path, work_guitar_path)
    
    result = split_guitar(work_guitar_path)
    
    # Extract paths from result list
    lead_path = rhythm_path = None
    for item in result:
        if item['name'] == 'lead_guitar':
            lead_path = item['path']
        elif item['name'] == 'rhythm_guitar':
            rhythm_path = item['path']
    
    if not lead_path or not os.path.exists(lead_path):
        raise RuntimeError(f"V3 splitter did not create lead output: {lead_path}")
    if not rhythm_path or not os.path.exists(rhythm_path):
        raise RuntimeError(f"V3 splitter did not create rhythm output: {rhythm_path}")
    
    return lead_path, rhythm_path


def organize_dataset(dataset_root, song_name, mixture_path, lead_path, rhythm_path, is_valid=False):
    """Organize files into dataset structure (Type 1: MUSDB format)."""
    split = 'valid' if is_valid else 'train'
    song_dir = Path(dataset_root) / split / song_name
    song_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy/convert files to the right format
    target_sr = 44100
    
    for src_path, stem_name in [
        (mixture_path, 'mixture'),
        (lead_path, 'lead_guitar'),
        (rhythm_path, 'rhythm_guitar'),
    ]:
        dst_path = song_dir / f'{stem_name}.wav'
        if not dst_path.exists():
            audio, sr = sf.read(src_path)
            if sr != target_sr:
                from torchaudio.functional import resample
                audio_t = torch.from_numpy(audio).float()
                if audio_t.ndim == 1:
                    audio_t = audio_t.unsqueeze(0)
                elif audio_t.shape[0] > 2:
                    audio_t = audio_t.T
                audio_t = resample(audio_t, sr, target_sr)
                audio = audio_t.numpy().T if audio_t.shape[0] <= 2 else audio_t.numpy()
            if audio.ndim == 1:
                audio = np.stack([audio, audio], axis=1)
            sf.write(str(dst_path), audio, target_sr)
    
    return str(song_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--songs_file', default='dataset_prep/songs_30.txt')
    parser.add_argument('--dataset_root', default='D:/qt/stemsplitteraiapp/dataset')
    parser.add_argument('--download_dir', default='D:/qt/stemsplitteraiapp/dataset/downloads')
    parser.add_argument('--work_dir', default='D:/qt/stemsplitteraiapp/dataset/work')
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--valid_ratio', type=float, default=0.1)
    parser.add_argument('--max_songs', type=int, default=3, help='0=all')
    args = parser.parse_args()
    
    os.makedirs(args.dataset_root, exist_ok=True)
    os.makedirs(args.download_dir, exist_ok=True)
    os.makedirs(args.work_dir, exist_ok=True)
    
    # Read song URLs
    urls = []
    with open(args.songs_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                url = line.split('#')[0].strip()
                if url:
                    urls.append((url, line.split('#')[-1].strip() if '#' in line else ''))
    
    if args.max_songs > 0:
        urls = urls[:args.max_songs]
    
    print(f'Processing {len(urls)} songs')
    print(f'Device: {args.device}')
    
    results = []
    for i, (url, desc) in enumerate(tqdm(urls, desc='Overall')):
        song_name = f'song_{i:03d}'
        print(f'\n[{i+1}/{len(urls)}] {desc}')
        
        try:
            # Step 1: Download audio
            audio_path = download_audio(url, args.download_dir, song_name)
            if not audio_path:
                print(f'  FAILED download: {url}')
                continue
            print(f'  Downloaded: {os.path.basename(audio_path)}')
            
            # Step 2: Extract guitar with demucs
            guitar_path = extract_guitar_demucs(audio_path, args.work_dir, args.device)
            print(f'  Guitar stem: {os.path.basename(guitar_path)}')
            
            # Step 3: V3+classifier lead/rhythm split
            lead_path, rhythm_path = split_lead_rhythm(guitar_path, args.work_dir)
            print(f'  Lead: {os.path.basename(lead_path)}, Rhythm: {os.path.basename(rhythm_path)}')
            
            # Step 4: Organize into dataset
            is_valid = i < max(1, int(len(urls) * args.valid_ratio))
            song_dir = organize_dataset(
                args.dataset_root, song_name,
                guitar_path, lead_path, rhythm_path,
                is_valid=is_valid
            )
            print(f'  Dataset: {song_dir}')
            results.append((song_name, song_dir, is_valid))
            
        except Exception as e:
            print(f'  ERROR: {e}')
            import traceback
            traceback.print_exc()
            continue
    
    print(f'\nDone. Processed {len(results)}/{len(urls)} songs')
    print(f'Train: {sum(1 for _,_,v in results if not v)}, Valid: {sum(1 for _,_,v in results if v)}')


if __name__ == '__main__':
    main()
