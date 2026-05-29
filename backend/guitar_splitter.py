import os
import numpy as np
import librosa
import soundfile as sf


def _resize_1d(arr, target_len):
    if arr.shape[0] == target_len:
        return arr
    return np.interp(
        np.linspace(0, arr.shape[0] - 1, target_len),
        np.arange(arr.shape[0]),
        arr,
    )


def _exponential_smoothing(mask, alpha=0.7, transient_weight=None):
    n = mask.shape[1]
    result = np.empty_like(mask)
    alpha_per_frame = np.broadcast_to(np.asarray(alpha), (n,))
    for f in range(mask.shape[0]):
        fwd = np.empty(n)
        fwd[0] = mask[f, 0]
        for t in range(1, n):
            a = alpha_per_frame[t] if transient_weight is None else alpha_per_frame[t] * (1.0 - transient_weight[t])
            fwd[t] = a * fwd[t-1] + (1.0 - a) * mask[f, t]
        bwd = np.empty(n)
        bwd[-1] = fwd[-1]
        for t in range(n-2, -1, -1):
            a = alpha_per_frame[t] if transient_weight is None else alpha_per_frame[t] * (1.0 - transient_weight[t])
            bwd[t] = a * bwd[t+1] + (1.0 - a) * fwd[t]
        result[f] = (fwd + bwd) * 0.5
    return result


def _transient_detection(y, sr, hop_length, n_frames):
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset = onset / (onset.max() + 1e-8)
    onset = _resize_1d(onset, n_frames)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop_length))
    flux = np.zeros(S.shape[1])
    for t in range(1, S.shape[1]):
        diff = S[:, t] - S[:, t-1]
        v = np.sum(diff[diff > 0])
        flux[t] = v
    flux = flux / (flux.max() + 1e-8)
    flux = _resize_1d(flux, n_frames)
    return np.maximum(onset, flux)


def _pitch_contour(y, sr, hop_length, n_frames):
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=hop_length)
    contour = np.zeros(n_frames)
    for t in range(min(n_frames, pitches.shape[1])):
        idx = np.argmax(magnitudes[:, t])
        if magnitudes[idx, t] > 0:
            contour[t] = pitches[idx, t]
    return contour


def _pitch_stability(contour, window=7):
    n = len(contour)
    stable = np.zeros(n)
    half = window // 2
    for t in range(n):
        start = max(0, t - half)
        end = min(n, t + half + 1)
        seg = contour[start:end]
        seg = seg[seg > 80]
        if len(seg) > 3:
            std = np.std(seg)
            stable[t] = 1.0 - min(std / 50.0, 1.0)
    return stable


def _percentile_rank(values):
    n = len(values)
    ranks = np.empty(n)
    ranks[np.argsort(values)] = np.arange(n) / n
    return ranks


def _extract_features(y, sr, S_full, S_h, pitch_stab, transient_w, hop_length, n_frames):
    centroid = librosa.feature.spectral_centroid(S=S_full, sr=sr)[0]
    centroid = _resize_1d(centroid, n_frames)

    bandwidth = librosa.feature.spectral_bandwidth(S=S_full, sr=sr)[0]
    bandwidth = _resize_1d(bandwidth, n_frames)

    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    zcr = _resize_1d(zcr, n_frames)

    flatness = librosa.feature.spectral_flatness(S=S_full)[0]
    flatness = _resize_1d(flatness, n_frames)
    flatness_log = np.log10(flatness + 1e-10)
    flatness_log = (flatness_log + 10) / 10.0

    total_energy = np.sum(S_full, axis=0) + 1e-8
    harmonic_energy = np.sum(S_h, axis=0)
    harm_ratio = harmonic_energy / total_energy

    return {
        'centroid': _percentile_rank(centroid),
        'bandwidth': _percentile_rank(bandwidth),
        'zcr': _percentile_rank(zcr),
        'flatness': _percentile_rank(flatness_log),
        'harm_ratio': _percentile_rank(harm_ratio),
        'sustain': _percentile_rank(pitch_stab),
        'transient': _percentile_rank(transient_w),
    }


def _classify_guitar(features):
    acoustic = np.zeros_like(features['centroid'])
    electric = np.zeros_like(features['centroid'])

    acoustic += np.where(features['centroid'] > 0.6, 0.25, 0.0)
    acoustic += np.where(features['transient'] > 0.6, 0.20, 0.0)
    acoustic += np.where(features['flatness'] > 0.6, 0.20, 0.0)
    acoustic += np.where(features['zcr'] > 0.6, 0.15, 0.0)
    acoustic += np.where(features['bandwidth'] > 0.6, 0.10, 0.0)
    acoustic += np.where(features['harm_ratio'] < 0.4, 0.10, 0.0)

    electric += np.where(features['sustain'] > 0.6, 0.30, 0.0)
    electric += np.where(features['harm_ratio'] > 0.6, 0.25, 0.0)
    electric += np.where(features['centroid'] < 0.4, 0.15, 0.0)
    electric += np.where(features['flatness'] < 0.4, 0.15, 0.0)
    electric += np.where(features['transient'] < 0.4, 0.15, 0.0)

    total = acoustic + electric + 1e-8
    acoustic_prob = acoustic / total
    electric_prob = electric / total
    return acoustic_prob, electric_prob


def split_guitar(guitar_path: str) -> list:
    """
    Split guitar stem into lead_guitar and rhythm_guitar.

    Pipeline:
      stereo -> mid/side -> STFT -> HPSS (margin=(1,2)) ->
      3-band feature extraction (0-250, 250-4k, 4k-16k) ->
      guitar-type classification (acoustic/electric) ->
      adaptive lead/rhythm scoring -> soft mask (exponent 0.7) ->
      mid-side aware masking (lead=center, rhythm=wide) ->
      transient-aware exponential smoothing ->
      Wiener refinement -> ISTFT -> stereo reconstruction.

    Returns [{"name": "lead_guitar", "path": ...},
             {"name": "rhythm_guitar", "path": ...}]
    """
    out_dir = os.path.dirname(guitar_path)
    base = os.path.splitext(os.path.basename(guitar_path))[0]

    y, sr = librosa.load(guitar_path, sr=44100, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y], axis=0)

    n_fft = 2048
    hop_length = 512
    eps = 1e-8

    mid = (y[0] + y[1]) * 0.5
    side = (y[0] - y[1]) * 0.5

    X_mid = librosa.stft(mid, n_fft=n_fft, hop_length=hop_length)
    X_side = librosa.stft(side, n_fft=n_fft, hop_length=hop_length)
    S_mid = np.abs(X_mid)
    S_side = np.abs(X_side)
    n_freqs, n_frames = S_mid.shape

    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    low_end = np.searchsorted(freqs, 250, side='right')
    mid_end = np.searchsorted(freqs, 4000, side='right')
    bands = [(0, low_end, 0.3), (low_end, mid_end, 1.0), (mid_end, n_freqs, 0.5)]

    S_h_mid, S_p_mid = librosa.decompose.hpss(S_mid, kernel_size=31, margin=(1.0, 2.0))
    S_h_side, S_p_side = librosa.decompose.hpss(S_side, kernel_size=31, margin=(1.0, 2.0))

    harm_mid = S_h_mid / (S_h_mid + S_p_mid + eps)
    harm_side = S_h_side / (S_h_side + S_p_side + eps)

    transient_w = _transient_detection(mid, sr, hop_length, n_frames)

    pitch_c = _pitch_contour(mid, sr, hop_length, n_frames)
    pitch_stab = _pitch_stability(pitch_c)

    # Guitar-type classification
    features = _extract_features(mid, sr, S_mid, S_h_mid, pitch_stab, transient_w, hop_length, n_frames)
    acoustic_prob, electric_prob = _classify_guitar(features)

    lead_bias = 1.0 - 0.4 * acoustic_prob
    rhythm_boost = 1.0 + 0.3 * acoustic_prob
    smooth_alpha = 0.7 - 0.3 * acoustic_prob
    wiener_scale = 1.0 - 0.5 * acoustic_prob

    lead_prior = np.exp(-0.5 * ((freqs - 2500) / 2000) ** 2)
    rhythm_prior = np.exp(-0.5 * ((freqs - 400) / 800) ** 2)

    combined_lead = np.zeros((n_freqs, n_frames))
    combined_rhythm = np.zeros((n_freqs, n_frames))

    for band_start, band_end, band_w in bands:
        bw = band_end - band_start
        if bw < 2:
            continue
        sub_S = S_mid[band_start:band_end, :]
        sub_freqs = freqs[band_start:band_end]

        sub_centroid = np.sum(sub_freqs[:, np.newaxis] * sub_S, axis=0) / (np.sum(sub_S, axis=0) + eps)
        sub_centroid = sub_centroid / sub_freqs.max()

        sub_rms = np.sqrt(np.mean(sub_S ** 2, axis=0))
        sub_rms = sub_rms / (sub_rms.max() + eps)

        sub_contrast = np.zeros(sub_S.shape[1])
        for t in range(sub_S.shape[1]):
            col = sub_S[:, t]
            if col.max() > 0:
                sub_contrast[t] = col.max() / (np.median(col[col > 0]) + eps) - 1.0
        sub_contrast = sub_contrast / (sub_contrast.max() + eps)

        lead_indicator = (0.30 * sub_centroid + 0.25 * sub_contrast + 0.25 * pitch_stab + 0.20 * sub_rms) * lead_bias
        rhythm_indicator = np.clip(1.0 - lead_indicator, 0.0, 1.0) * rhythm_boost

        sub_harm = harm_mid[band_start:band_end, :]
        sub_lead_prior = lead_prior[band_start:band_end, np.newaxis]
        sub_rhythm_prior = rhythm_prior[band_start:band_end, np.newaxis]

        combined_lead[band_start:band_end, :] = sub_lead_prior * lead_indicator[np.newaxis, :] * sub_harm * band_w
        combined_rhythm[band_start:band_end, :] = sub_rhythm_prior * rhythm_indicator[np.newaxis, :] * (1.0 - sub_harm) * band_w

    mask = combined_lead / (combined_lead + combined_rhythm + eps)
    mask = np.nan_to_num(mask, nan=0.5, posinf=0.95, neginf=0.05)
    mask = np.clip(mask, 0.0, 1.0)
    mask = mask ** 0.7

    mask = _exponential_smoothing(mask, alpha=smooth_alpha, transient_weight=transient_w)
    mask = np.clip(mask, 0.05, 0.95)

    mask_mid = mask
    mask_side = mask * 0.5

    lead_mid_spec = mask_mid * X_mid
    rhythm_mid_spec = (1.0 - mask_mid) * X_mid
    lead_side_spec = mask_side * X_side
    rhythm_side_spec = (1.0 - mask_side) * X_side

    # Wiener refinement with adaptive strength
    lead_mid_mag = np.abs(lead_mid_spec)
    rhythm_mid_mag = np.abs(rhythm_mid_spec)
    wiener_mid = lead_mid_mag ** 2 / (lead_mid_mag ** 2 + rhythm_mid_mag ** 2 + eps)
    wiener_mid = np.nan_to_num(wiener_mid, nan=0.5)
    blend_mid = wiener_scale[np.newaxis, :] * wiener_mid + (1.0 - wiener_scale[np.newaxis, :]) * mask_mid
    lead_mid_ref = blend_mid * X_mid
    rhythm_mid_ref = (1.0 - blend_mid) * X_mid

    lead_side_mag = np.abs(lead_side_spec)
    rhythm_side_mag = np.abs(rhythm_side_spec)
    wiener_side = lead_side_mag ** 2 / (lead_side_mag ** 2 + rhythm_side_mag ** 2 + eps)
    wiener_side = np.nan_to_num(wiener_side, nan=0.5)
    blend_side = wiener_scale[np.newaxis, :] * wiener_side + (1.0 - wiener_scale[np.newaxis, :]) * mask_side
    lead_side_ref = blend_side * X_side
    rhythm_side_ref = (1.0 - blend_side) * X_side

    lead_mid_audio = librosa.istft(lead_mid_ref, hop_length=hop_length)
    rhythm_mid_audio = librosa.istft(rhythm_mid_ref, hop_length=hop_length)
    lead_side_audio = librosa.istft(lead_side_ref, hop_length=hop_length)
    rhythm_side_audio = librosa.istft(rhythm_side_ref, hop_length=hop_length)

    lim = min(len(lead_mid_audio), len(lead_side_audio), len(rhythm_mid_audio), len(rhythm_side_audio))
    lead_L = lead_mid_audio[:lim] + lead_side_audio[:lim]
    lead_R = lead_mid_audio[:lim] - lead_side_audio[:lim]
    rhythm_L = rhythm_mid_audio[:lim] + rhythm_side_audio[:lim]
    rhythm_R = rhythm_mid_audio[:lim] - rhythm_side_audio[:lim]

    lead_stereo = np.column_stack([lead_L, lead_R])
    rhythm_stereo = np.column_stack([rhythm_L, rhythm_R])

    peak = max(np.max(np.abs(lead_stereo)), np.max(np.abs(rhythm_stereo)), eps)
    lead_stereo = np.clip(lead_stereo / peak * 0.95, -1.0, 1.0)
    rhythm_stereo = np.clip(rhythm_stereo / peak * 0.95, -1.0, 1.0)

    lead_path = os.path.join(out_dir, f"{base}_lead_guitar.wav")
    rhythm_path = os.path.join(out_dir, f"{base}_rhythm_guitar.wav")

    sf.write(lead_path, lead_stereo, sr)
    sf.write(rhythm_path, rhythm_stereo, sr)

    return [
        {"name": "lead_guitar", "path": lead_path},
        {"name": "rhythm_guitar", "path": rhythm_path},
    ]
