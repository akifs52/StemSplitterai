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


def min_energy_loss(y_pred: torch.Tensor, y_true: torch.Tensor,
                     x: Optional[torch.Tensor] = None,
                     threshold: float = 0.01) -> torch.Tensor:
    if x is None:
        return torch.tensor(0.0, device=y_pred.device)
    input_energy = torch.mean(x ** 2) + 1e-8
    output_energy = torch.mean(y_pred ** 2) + 1e-8
    ratio = output_energy / (input_energy + 1e-8)
    penalty = F.relu(threshold - ratio)
    return penalty


class CompositeProLoss:
    def __init__(self, config: dict):
        if hasattr(config, 'loss'):
            loss_cfg = config.loss
        elif isinstance(config, dict):
            loss_cfg = config.get('loss', {})
        else:
            loss_cfg = {}

        self.weights = {
            'l1_waveform': getattr(loss_cfg, 'l1_waveform_coef', 1.0) if hasattr(loss_cfg, 'l1_waveform_coef') else loss_cfg.get('l1_waveform_coef', 1.0),
            'multi_stft': getattr(loss_cfg, 'multi_stft_coef', 1.0) if hasattr(loss_cfg, 'multi_stft_coef') else loss_cfg.get('multi_stft_coef', 1.0),
            'spectral_convergence': getattr(loss_cfg, 'spectral_convergence_coef', 0.5) if hasattr(loss_cfg, 'spectral_convergence_coef') else loss_cfg.get('spectral_convergence_coef', 0.5),
            'min_energy': getattr(loss_cfg, 'min_energy_coef', 2.0) if hasattr(loss_cfg, 'min_energy_coef') else loss_cfg.get('min_energy_coef', 2.0),
        }
        self.threshold = getattr(loss_cfg, 'min_energy_threshold', 0.01) if hasattr(loss_cfg, 'min_energy_threshold') else loss_cfg.get('min_energy_threshold', 0.01)
        self.flags = {
            'l1_waveform': getattr(loss_cfg, 'l1_waveform', True) if hasattr(loss_cfg, 'l1_waveform') else loss_cfg.get('l1_waveform', True),
            'multi_stft': getattr(loss_cfg, 'multi_stft', True) if hasattr(loss_cfg, 'multi_stft') else loss_cfg.get('multi_stft', True),
            'spectral_convergence': getattr(loss_cfg, 'spectral_convergence', True) if hasattr(loss_cfg, 'spectral_convergence') else loss_cfg.get('spectral_convergence', True),
            'min_energy': getattr(loss_cfg, 'min_energy', True) if hasattr(loss_cfg, 'min_energy') else loss_cfg.get('min_energy', True),
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
        if self.flags['min_energy']:
            total += self.weights['min_energy'] * min_energy_loss(y_pred, y_true, x, self.threshold)
        return total


def choice_loss_pro(config) -> Callable:
    return CompositeProLoss(config)
