import os
import sys
import argparse
import numpy as np
import torch
import librosa
import soundfile as sf
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(__file__))
from utils.settings import load_config, get_model_from_config
from utils.model_utils import demix, wiener_refinement
from utils.post_pro import process_stems


def parse_args():
    parser = argparse.ArgumentParser(description="Professional lead/rhythm guitar separation inference")
    parser.add_argument("--config_path", type=str, default="configs/config_leadrhythm_pro.yaml",
                        help="Path to model config")
    parser.add_argument("--checkpoint", type=str, required=True,
                        help="Path to model checkpoint (.ckpt)")
    parser.add_argument("--input", type=str, required=True,
                        help="Input audio file or directory")
    parser.add_argument("--output", type=str, required=True,
                        help="Output directory for separated stems")
    parser.add_argument("--device_ids", nargs="+", type=int, default=[0],
                        help="GPU device IDs")
    parser.add_argument("--overlap", type=int, default=4,
                        help="Overlap factor for chunked inference")
    parser.add_argument("--wiener", action="store_true", default=True,
                        help="Apply Wiener refinement")
    parser.add_argument("--post_process", action="store_true", default=True,
                        help="Apply DSP post-processing")
    parser.add_argument("--save_individual", action="store_true", default=True,
                        help="Save individual stem files")
    return parser.parse_args()


def load_model(config, checkpoint_path, device):
    model = get_model_from_config(config, args_type='train')
    ckpt = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    if 'model_state_dict' in ckpt:
        state_dict = ckpt['model_state_dict']
    elif 'state_dict' in ckpt:
        state_dict = ckpt['state_dict']
    elif 'state' in ckpt:
        state_dict = ckpt['state']
    else:
        state_dict = ckpt
    model.load_state_dict(state_dict, strict=False)
    model.eval()
    model.to(device)
    return model


def separate_file(model, config, audio_path, device, overlap=4,
                  use_wiener=True, use_post_process=True):
    audio, sr = librosa.load(audio_path, sr=config.audio.sample_rate, mono=False)
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=0)
    elif audio.shape[0] > 2:
        audio = audio[:2]
    mix = audio.copy()

    config.inference.num_overlap = overlap
    config.audio.chunk_size = config.audio.chunk_size

    result = demix(config, model, mix, device, model_type='mel_band_roformer', pbar=True)
    if isinstance(result, dict):
        stems = result
    elif isinstance(result, np.ndarray):
        instr_names = config.training.instruments
        stems = {name: result[i] for i, name in enumerate(instr_names)}

    if use_wiener and 'lead_guitar' in stems and 'rhythm_guitar' in stems and len(stems) == 2:
        lead_ref, rhythm_ref = wiener_refinement(
            mix.mean(axis=0) if mix.shape[0] == 2 else mix,
            stems['lead_guitar'].mean(axis=0) if stems['lead_guitar'].shape[0] == 2 else stems['lead_guitar'],
            stems['rhythm_guitar'].mean(axis=0) if stems['rhythm_guitar'].shape[0] == 2 else stems['rhythm_guitar'],
            alpha=config.inference.get('wiener_alpha', 0.5),
            n_fft=config.audio.n_fft,
            hop_length=config.audio.hop_length
        )
        stems['lead_guitar'] = np.stack([lead_ref, lead_ref], axis=0)
        stems['rhythm_guitar'] = np.stack([rhythm_ref, rhythm_ref], axis=0)

    if use_post_process:
        stems = process_stems(stems, mix, config, sample_rate=config.audio.sample_rate)

    return stems


def main():
    args = parse_args()
    config = load_config(args.config_path)
    device = torch.device(f'cuda:{args.device_ids[0]}' if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')

    model = load_model(config, args.checkpoint, device)
    print(f'Model loaded from {args.checkpoint}')

    if os.path.isfile(args.input):
        files = [args.input]
    elif os.path.isdir(args.input):
        ext = ('.wav', '.mp3', '.flac', '.m4a', '.ogg')
        files = [os.path.join(args.input, f) for f in sorted(os.listdir(args.input))
                 if f.lower().endswith(ext)]
    else:
        print(f'Input not found: {args.input}')
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    for fpath in tqdm(files, desc='Separating files'):
        try:
            stems = separate_file(model, config, fpath, device,
                                  overlap=args.overlap,
                                  use_wiener=args.wiener,
                                  use_post_process=args.post_process)
            base = os.path.splitext(os.path.basename(fpath))[0]
            out_dir = os.path.join(args.output, base)
            os.makedirs(out_dir, exist_ok=True)
            for stem_name, stem_audio in stems.items():
                out_path = os.path.join(out_dir, f'{stem_name}.wav')
                sf.write(out_path, stem_audio.T, config.audio.sample_rate)
            mix_out = os.path.join(out_dir, 'mixture.wav')
            mix_audio, _ = librosa.load(fpath, sr=config.audio.sample_rate, mono=False)
            if mix_audio.ndim == 1:
                mix_audio = np.stack([mix_audio, mix_audio], axis=0)
            sf.write(mix_out, mix_audio.T, config.audio.sample_rate)
            print(f'  Saved to {out_dir}')
        except Exception as e:
            print(f'  Error processing {fpath}: {e}')
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
