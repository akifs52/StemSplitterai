import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Callable


def l1_waveform_loss(y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
    return F.l1_loss(y_pred, y_true)


def multi_resolution_stft_loss(y_pred: torch.Tensor, y_true: torch.Tensor,
                                 window_sizes=(4096, 2048, 1024, 512, 256),
                                 hop_size=147, normalized=False) -> torch.Tensor:
    loss = 0.0
    for ws in window_sizes:
        y_pred_spec = torch.stft(y_pred.reshape(-1, y_pred.shape[-1]),
                                 n_fft=ws, hop_length=hop_size,
                                 win_length=ws, window=torch.hann_window(ws, device=y_pred.device),
                                 return_complex=True, normalized=normalized)
        y_true_spec = torch.stft(y_true.reshape(-1, y_true.shape[-1]),
                                 n_fft=ws, hop_length=hop_size,
                                 win_length=ws, window=torch.hann_window(ws, device=y_true.device),
                                 return_complex=True, normalized=normalized)
        loss += F.l1_loss(y_pred_spec.abs(), y_true_spec.abs())
    return loss / len(window_sizes)


def spectral_convergence_loss(y_pred: torch.Tensor, y_true: torch.Tensor,
                               n_fft=2048, hop_length=512) -> torch.Tensor:
    y_pred_spec = torch.stft(y_pred.reshape(-1, y_pred.shape[-1]),
                             n_fft=n_fft, hop_length=hop_length,
                             window=torch.hann_window(n_fft, device=y_pred.device),
                             return_complex=True)
    y_true_spec = torch.stft(y_true.reshape(-1, y_true.shape[-1]),
                             n_fft=n_fft, hop_length=hop_length,
                             window=torch.hann_window(n_fft, device=y_true.device),
                             return_complex=True)
    pred_mag = y_pred_spec.abs()
    true_mag = y_true_spec.abs()
    numer = torch.norm(pred_mag - true_mag, p='fro')
    denom = torch.norm(true_mag, p='fro') + 1e-8
    return numer / denom


def si_sdr_loss(y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
    y_true_mean = torch.mean(y_true, dim=-1, keepdim=True)
    y_pred_mean = torch.mean(y_pred, dim=-1, keepdim=True)
    y_true_zm = y_true - y_true_mean
    y_pred_zm = y_pred - y_pred_mean
    scale = (y_pred_zm * y_true_zm).sum(dim=-1, keepdim=True) / (
        (y_true_zm ** 2).sum(dim=-1, keepdim=True) + 1e-8
    )
    s_target = scale * y_true_zm
    e_noise = y_pred_zm - s_target
    si_sdr_val = 10 * torch.log10(
        (s_target ** 2).sum(dim=-1) / ((e_noise ** 2).sum(dim=-1) + 1e-8) + 1e-8
    )
    return -si_sdr_val.mean()


def stem_leakage_loss(y_pred: torch.Tensor, y_true: torch.Tensor,
                       n_fft=2048, hop_length=512) -> torch.Tensor:
    batch, num_stems, channels, samples = y_pred.shape
    if num_stems != 2:
        return torch.tensor(0.0, device=y_pred.device)

    lead_pred = y_pred[:, 0].reshape(-1, samples)
    rhythm_pred = y_pred[:, 1].reshape(-1, samples)
    lead_true = y_true[:, 0].reshape(-1, samples)
    rhythm_true = y_true[:, 1].reshape(-1, samples)

    def _mag(x):
        return torch.stft(x, n_fft=n_fft, hop_length=hop_length,
                          window=torch.hann_window(n_fft, device=x.device),
                          return_complex=True).abs()

    mag_lp = _mag(lead_pred)
    mag_rp = _mag(rhythm_pred)
    mag_lt = _mag(lead_true)
    mag_rt = _mag(rhythm_true)

    n = mag_lp.numel()
    lead_leak = (mag_lp * mag_rt).sum() / n
    rhythm_leak = (mag_rp * mag_lt).sum() / n
    return lead_leak + rhythm_leak


def stereo_consistency_loss(y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
    batch, num_stems, channels, samples = y_pred.shape
    if channels != 2:
        return torch.tensor(0.0, device=y_pred.device)

    loss = 0.0
    for s in range(num_stems):
        pred_L = y_pred[:, s, 0]
        pred_R = y_pred[:, s, 1]
        true_L = y_true[:, s, 0]
        true_R = y_true[:, s, 1]

        pred_corr = F.cosine_similarity(pred_L, pred_R, dim=-1).mean()
        true_corr = F.cosine_similarity(true_L, true_R, dim=-1).mean()
        loss += F.l1_loss(pred_corr, true_corr)
    return loss / num_stems


def center_aware_lead_loss(y_pred: torch.Tensor, y_true: torch.Tensor,
                            mid_weight=1.5, side_weight=0.5) -> torch.Tensor:
    batch, num_stems, channels, samples = y_pred.shape
    if num_stems < 1:
        return torch.tensor(0.0, device=y_pred.device)

    loss = 0.0
    for s in range(num_stems):
        if channels == 2:
            pred_L = y_pred[:, s, 0:1, :]
            pred_R = y_pred[:, s, 1:2, :]
            true_L = y_true[:, s, 0:1, :]
            true_R = y_true[:, s, 1:2, :]
            pred_mid = (pred_L + pred_R) / 2
            pred_side = (pred_L - pred_R) / 2
            true_mid = (true_L + true_R) / 2
            true_side = (true_L - true_R) / 2
            loss += mid_weight * F.l1_loss(pred_mid, true_mid)
            loss += side_weight * F.l1_loss(pred_side, true_side)
        else:
            loss += F.l1_loss(y_pred[:, s], y_true[:, s])
    return loss / num_stems


class CompositeProLoss:
    def __init__(self, config: dict):
        loss_cfg = config.get('loss', {})
        self.weights = {
            'l1_waveform': loss_cfg.get('l1_waveform_coef', 1.0),
            'multi_stft': loss_cfg.get('multi_stft_coef', 1.0),
            'spectral_convergence': loss_cfg.get('spectral_convergence_coef', 0.5),
            'si_sdr': loss_cfg.get('si_sdr_coef', 0.1),
            'stem_leakage': loss_cfg.get('stem_leakage_coef', 0.3),
            'stereo_consistency': loss_cfg.get('stereo_consistency_coef', 0.2),
            'center_aware_lead': loss_cfg.get('center_aware_lead_coef', 0.4),
        }
        self.flags = {
            'l1_waveform': loss_cfg.get('l1_waveform', True),
            'multi_stft': loss_cfg.get('multi_stft', True),
            'spectral_convergence': loss_cfg.get('spectral_convergence', True),
            'si_sdr': loss_cfg.get('si_sdr', True),
            'stem_leakage': loss_cfg.get('stem_leakage', True),
            'stereo_consistency': loss_cfg.get('stereo_consistency', True),
            'center_aware_lead': loss_cfg.get('center_aware_lead', True),
        }

    def __call__(self, y_pred: torch.Tensor, y_true: torch.Tensor,
                 x: Optional[torch.Tensor] = None) -> torch.Tensor:
        total = 0.0
        if self.flags['l1_waveform']:
            total += self.weights['l1_waveform'] * l1_waveform_loss(y_pred, y_true)
        if self.flags['multi_stft']:
            total += self.weights['multi_stft'] * multi_resolution_stft_loss(y_pred, y_true)
        if self.flags['spectral_convergence']:
            total += self.weights['spectral_convergence'] * spectral_convergence_loss(y_pred, y_true)
        if self.flags['si_sdr']:
            total += self.weights['si_sdr'] * si_sdr_loss(y_pred, y_true)
        if self.flags['stem_leakage']:
            total += self.weights['stem_leakage'] * stem_leakage_loss(y_pred, y_true)
        if self.flags['stereo_consistency']:
            total += self.weights['stereo_consistency'] * stereo_consistency_loss(y_pred, y_true)
        if self.flags['center_aware_lead']:
            total += self.weights['center_aware_lead'] * center_aware_lead_loss(y_pred, y_true)
        return total


def choice_loss_pro(config) -> Callable:
    return CompositeProLoss(config)
