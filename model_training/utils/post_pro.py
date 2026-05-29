import numpy as np
import librosa


def transient_enhance(audio: np.ndarray, sample_rate=44100, blend=0.3) -> np.ndarray:
    onset_frames = librosa.onset.onset_detect(y=audio.mean(axis=0) if audio.ndim > 1 else audio,
                                               sr=sample_rate, hop_length=512,
                                               backtrack=True, units='samples')
    if len(onset_frames) < 2:
        return audio
    onset_env = np.zeros(audio.shape[-1], dtype=np.float32)
    for o in onset_frames:
        onset_env[max(0, o - 256): min(audio.shape[-1], o + 256)] = 1.0
    onset_env = onset_env[:audio.shape[-1]]
    onset_env = librosa.util.normalize(onset_env)
    onset_env = np.clip(onset_env, 0, 1)
    if audio.ndim > 1:
        onset_env = onset_env[np.newaxis, :]
    blend_mask = blend * onset_env
    return audio * (1 - blend_mask) + audio * blend_mask


def harmonic_enhance(audio: np.ndarray, boost_db=1.0, sample_rate=44100) -> np.ndarray:
    if audio.shape[-1] < 2048:
        return audio
    try:
        harm, perc = librosa.decompose.hpss(
            librosa.stft(audio.mean(axis=0) if audio.ndim > 1 else audio),
            kernel_size=31, margin=3.0
        )
        harm = librosa.istft(harm, length=audio.shape[-1])
        boost_linear = 10 ** (boost_db / 20)
        harm_boosted = harm * (boost_linear - 1.0)
        if audio.ndim > 1:
            harm_boosted = np.stack([harm_boosted] * audio.shape[0])
            harm_boosted = harm_boosted.reshape(audio.shape)
        return audio + harm_boosted
    except Exception:
        return audio


def spectral_denoise(audio: np.ndarray, noise_floor_percentile=10, sample_rate=44100) -> np.ndarray:
    if audio.shape[-1] < 2048:
        return audio
    try:
        n_fft = 2048
        hop_length = 512
        S = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
        mag = np.abs(S)
        phase = np.angle(S)
        noise_floor = np.percentile(mag, noise_floor_percentile, axis=-1, keepdims=True)
        mag_s = np.maximum(mag, 1e-8)
        mask = mag_s ** 2 / (mag_s ** 2 + noise_floor ** 2)
        S_clean = mag * mask * np.exp(1j * phase)
        cleaned = librosa.istft(S_clean, hop_length=hop_length, length=audio.shape[-1])
        if audio.ndim > 1:
            return cleaned.reshape(audio.shape)
        return cleaned
    except Exception:
        return audio


def stereo_restore(audio: np.ndarray, reference_corr=None) -> np.ndarray:
    if audio.ndim < 2 or audio.shape[0] != 2:
        return audio
    if reference_corr is None:
        return audio
    target_corr = np.clip(reference_corr, -1, 1)
    L, R = audio[0], audio[1]
    L = L - L.mean()
    R = R - R.mean()
    current_corr = np.corrcoef(L, R)[0, 1]
    if abs(current_corr - target_corr) < 0.01:
        return audio
    mid = (L + R) / 2
    side = (L - R) / 2
    alpha = max(-1, min(1, (1 - target_corr) / (1 + 1e-8)))
    current_alpha = max(-1, min(1, (1 - current_corr) / (1 + 1e-8)))
    scale = alpha / (current_alpha + 1e-8)
    side = side * scale
    L_new = mid + side
    R_new = mid - side
    return np.stack([L_new, R_new], axis=0)


def process_stems(stems: dict, mix: np.ndarray, config: dict, sample_rate=44100) -> dict:
    inf_cfg = config.get('inference', {})
    if not inf_cfg.get('post_process', True):
        return stems
    result = {}
    for stem_name, audio in stems.items():
        if inf_cfg.get('transient_enhance', True):
            audio = transient_enhance(audio, sample_rate)
        if inf_cfg.get('harmonic_enhance', True):
            audio = harmonic_enhance(audio, sample_rate=44100)
        if inf_cfg.get('spectral_denoise', True):
            audio = spectral_denoise(audio, sample_rate=sample_rate)
        if inf_cfg.get('stereo_restore', True) and mix is not None:
            if mix.ndim > 1 and mix.shape[0] == 2:
                ref_corr = np.corrcoef(mix[0], mix[1])[0, 1]
                audio = stereo_restore(audio, ref_corr)
        result[stem_name] = audio
    return result
