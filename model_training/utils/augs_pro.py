import random
import math
import numpy as np
import torch


def apply_gain(audio: np.ndarray, gain_min=0.7, gain_max=1.3) -> np.ndarray:
    gain = random.uniform(gain_min, gain_max)
    return audio * gain


def apply_stereo_width(audio: np.ndarray, width_min=0.5, width_max=1.5) -> np.ndarray:
    if audio.shape[0] != 2:
        return audio
    mid = (audio[0] + audio[1]) / 2
    side = (audio[0] - audio[1]) / 2
    width = random.uniform(width_min, width_max)
    side = side * width
    audio = np.stack([mid + side, mid - side], axis=0)
    return audio


def apply_eq(audio: np.ndarray, sample_rate=44100) -> np.ndarray:
    try:
        import pedalboard as pb
        eq = pb.SevenBandParametricEQ(
            low_shelf_gain_db=random.uniform(-6, 6),
            parametric1_gain_db=random.uniform(-6, 6),
            parametric2_gain_db=random.uniform(-6, 6),
            parametric3_gain_db=random.uniform(-6, 6),
            parametric4_gain_db=random.uniform(-6, 6),
            parametric5_gain_db=random.uniform(-6, 6),
            high_shelf_gain_db=random.uniform(-6, 6),
        )
        board = pb.Pedalboard([eq], sample_rate=sample_rate)
        return board(audio.T, sample_rate).T
    except Exception:
        return audio


def apply_cabinet(audio: np.ndarray, sample_rate=44100) -> np.ndarray:
    try:
        import pedalboard as pb
        low_cut = random.uniform(80, 200)
        high_cut = random.uniform(4000, 8000)
        board = pb.Pedalboard([
            pb.HighpassFilter(cutoff_frequency_hz=low_cut),
            pb.LowpassFilter(cutoff_frequency_hz=high_cut),
        ], sample_rate=sample_rate)
        return board(audio.T, sample_rate).T
    except Exception:
        return audio


def apply_saturation(audio: np.ndarray, drive_min=0.0, drive_max=0.3) -> np.ndarray:
    drive = random.uniform(drive_min, drive_max)
    if drive <= 0:
        return audio
    gain_factor = 1 + drive
    audio = audio * gain_factor
    audio = np.tanh(audio)
    peak = np.max(np.abs(audio)) + 1e-8
    if peak > 1.0:
        audio = audio / peak
    return audio


def apply_reverb(audio: np.ndarray, wet_min=0.0, wet_max=0.15, sample_rate=44100) -> np.ndarray:
    wet = random.uniform(wet_min, wet_max)
    if wet <= 0:
        return audio
    try:
        import pedalboard as pb
        reverb = pb.Reverb(
            room_size=random.uniform(0.1, 0.5),
            damping=random.uniform(0.1, 0.5),
            wet_level=wet,
            dry_level=1.0 - wet,
            width=1.0,
        )
        board = pb.Pedalboard([reverb], sample_rate=sample_rate)
        return board(audio.T, sample_rate).T
    except Exception:
        return audio


def apply_panning(audio: np.ndarray, pan_min=0.8, pan_max=1.0) -> np.ndarray:
    if audio.shape[0] != 2:
        return audio
    left_gain = random.uniform(pan_min, pan_max)
    right_gain = random.uniform(pan_min, pan_max)
    audio[0] = audio[0] * left_gain
    audio[1] = audio[1] * right_gain
    return audio


def apply_ms_rotation(audio: np.ndarray, angle_max_deg=15.0) -> np.ndarray:
    if audio.shape[0] != 2:
        return audio
    angle = random.uniform(-angle_max_deg, angle_max_deg)
    theta = math.radians(angle)
    c, s = math.cos(theta), math.sin(theta)
    rot = np.array([[c, -s], [s, c]])
    audio = rot @ audio
    return audio


def apply_time_masking(audio: np.ndarray, max_sec=0.3, sample_rate=44100) -> np.ndarray:
    max_len = int(max_sec * sample_rate)
    if max_len <= 0 or audio.shape[-1] <= max_len:
        return audio
    mask_len = random.randint(16, max_len)
    start = random.randint(0, audio.shape[-1] - mask_len)
    audio[..., start:start + mask_len] = 0.0
    return audio


def apply_freq_masking(audio: np.ndarray, max_bands=3, n_fft=2048, hop_length=512) -> np.ndarray:
    if audio.shape[-1] < n_fft:
        return audio
    n_bands = min(max_bands, n_fft // 2)
    num_mask = random.randint(1, n_bands)
    try:
        import librosa
        S = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
        freq_bins = S.shape[-2]
        masked = np.zeros(freq_bins, dtype=bool)
        for _ in range(num_mask):
            band_width = random.randint(1, min(10, freq_bins // 4))
            center = random.randint(0, freq_bins - 1)
            lo = max(0, center - band_width // 2)
            hi = min(freq_bins, center + band_width // 2)
            if not masked[lo:hi].all():
                S[..., lo:hi, :] = 0.0
                masked[lo:hi] = True
        audio = librosa.istft(S, hop_length=hop_length, length=audio.shape[-1])
    except Exception:
        pass
    return audio


class GuitarAugmentationPipeline:
    def __init__(self, config: dict):
        aug_cfg = config.get('augmentations', {})
        self.enabled = aug_cfg.get('enable', True)
        self.sample_rate = config.get('audio', {}).get('sample_rate', 44100)
        self.params = {
            'gain': (aug_cfg.get('loudness_min', 0.7), aug_cfg.get('loudness_max', 1.3)),
            'stereo_width': (aug_cfg.get('stereo_width_min', 0.5), aug_cfg.get('stereo_width_max', 1.5)),
            'saturation': (aug_cfg.get('saturation_drive_min', 0.0), aug_cfg.get('saturation_drive_max', 0.3)),
            'reverb': (aug_cfg.get('reverb_wet_min', 0.0), aug_cfg.get('reverb_wet_max', 0.15)),
            'panning': (aug_cfg.get('panning_min', 0.8), aug_cfg.get('panning_max', 1.0)),
            'ms_rotation': aug_cfg.get('ms_rotation_angle_max', 15.0),
            'time_mask': aug_cfg.get('time_mask_max_sec', 0.3),
            'freq_mask': aug_cfg.get('freq_mask_max_bands', 3),
        }
        self.flags = {
            'gain': aug_cfg.get('loudness', True),
            'stereo_width': aug_cfg.get('stereo_width', True),
            'eq': aug_cfg.get('eq', True),
            'cabinet': aug_cfg.get('cabinet', True),
            'saturation': aug_cfg.get('saturation', True),
            'reverb': aug_cfg.get('reverb', True),
            'panning': aug_cfg.get('panning', True),
            'ms_rotation': aug_cfg.get('ms_rotation', True),
            'time_mask': aug_cfg.get('time_mask', True),
            'freq_mask': aug_cfg.get('freq_mask', True),
        }

    def __call__(self, audio: np.ndarray, instr_name: str = '') -> np.ndarray:
        if not self.enabled:
            return audio
        audio = audio.copy()
        if self.flags['gain']:
            audio = apply_gain(audio, *self.params['gain'])
        if self.flags['stereo_width']:
            audio = apply_stereo_width(audio, *self.params['stereo_width'])
        if self.flags['ms_rotation']:
            audio = apply_ms_rotation(audio, self.params['ms_rotation'])
        if self.flags['panning']:
            audio = apply_panning(audio, *self.params['panning'])
        if self.flags['eq']:
            audio = apply_eq(audio, self.sample_rate)
        if self.flags['cabinet']:
            audio = apply_cabinet(audio, self.sample_rate)
        if self.flags['saturation']:
            audio = apply_saturation(audio, *self.params['saturation'])
        if self.flags['reverb']:
            audio = apply_reverb(audio, *self.params['reverb'], self.sample_rate)
        if self.flags['time_mask']:
            audio = apply_time_masking(audio, self.params['time_mask'], self.sample_rate)
        if self.flags['freq_mask']:
            audio = apply_freq_masking(audio, self.params['freq_mask'])
        return audio
