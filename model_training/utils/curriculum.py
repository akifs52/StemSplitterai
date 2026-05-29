import math
import numpy as np
import torch
from torch.utils.data import Sampler, Dataset


def compute_difficulty(track_dir: str) -> float:
    try:
        import librosa
        lead_path = f'{track_dir}/lead_guitar.wav'
        rhythm_path = f'{track_dir}/rhythm_guitar.wav'
        try:
            lead, sr = librosa.load(lead_path, sr=None, mono=True)
            rhythm, _ = librosa.load(rhythm_path, sr=None, mono=True)
        except Exception:
            return 0.5
        if len(lead) == 0 or len(rhythm) == 0:
            return 0.5
        min_len = min(len(lead), len(rhythm))
        lead = lead[:min_len]
        rhythm = rhythm[:min_len]
        lead_spec = np.abs(librosa.stft(lead))
        rhythm_spec = np.abs(librosa.stft(rhythm))
        lead_sc = np.std(librosa.feature.spectral_centroid(S=lead_spec, sr=sr))
        rhythm_sc = np.std(librosa.feature.spectral_centroid(S=rhythm_spec, sr=sr))
        spectral_variability = float(lead_sc + rhythm_sc)
        lead_pan = float(np.abs(np.corrcoef(
            librosa.load(track_dir + '/lead_guitar.wav', sr=None, mono=False)[0][0],
            librosa.load(track_dir + '/lead_guitar.wav', sr=None, mono=False)[0][1]
        )[0, 1])) if False else 0.5
        overlay = float(np.abs(np.corrcoef(lead, rhythm)[0, 1]))
        difficulty = 0.3 * (spectral_variability / 2000) + 0.3 * abs(overlay) + 0.2 * (1 - lead_pan)
        return float(np.clip(difficulty, 0.0, 1.0))
    except Exception:
        return 0.5


class CurriculumSampler(Sampler):
    def __init__(self, dataset: Dataset, epoch: int = 0, num_epochs: int = 50):
        self.dataset = dataset
        self.num_epochs = num_epochs
        self.epoch = epoch
        self.indices = list(range(len(dataset)))
        np.random.seed(0)
        np.random.shuffle(self.indices)

    def set_epoch(self, epoch: int):
        self.epoch = epoch
        progress = epoch / max(self.num_epochs - 1, 1)
        keep_ratio = 1.0 - 0.5 * max(0, 1.0 - progress * 3)
        keep_ratio = max(0.3, min(1.0, keep_ratio))
        num_keep = max(1, int(len(self.indices) * keep_ratio))
        seed = 42 + epoch
        rng = np.random.RandomState(seed)
        easy = list(self.indices[:num_keep])
        rng.shuffle(easy)
        self.epoch_indices = easy

    def __iter__(self):
        return iter(getattr(self, 'epoch_indices', self.indices))

    def __len__(self):
        return len(getattr(self, 'epoch_indices', self.indices))
