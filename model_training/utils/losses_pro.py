import torch
import torch.nn.functional as F
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


def _cfg_get(cfg, name: str, default):
    if hasattr(cfg, name):
        return getattr(cfg, name)
    if isinstance(cfg, dict):
        return cfg.get(name, default)
    return default


def _stem_reduce_dims(y: torch.Tensor) -> tuple:
    if y.dim() >= 4:
        return tuple(range(2, y.dim()))
    if y.dim() == 3:
        return tuple(range(1, y.dim()))
    return tuple(range(y.dim()))


def min_energy_loss(y_pred: torch.Tensor, y_true: torch.Tensor,
                    threshold: float = 0.1,
                    min_target_energy: float = 1e-7) -> torch.Tensor:
    reduce_dims = _stem_reduce_dims(y_pred)
    pred_energy = torch.mean(y_pred ** 2, dim=reduce_dims)
    true_energy = torch.mean(y_true ** 2, dim=reduce_dims)
    active = true_energy > min_target_energy

    if not torch.any(active):
        return y_pred.new_tensor(0.0)

    ratio = pred_energy / true_energy.clamp_min(1e-8)
    penalty = F.relu(threshold - ratio)
    return penalty[active].mean()


def si_sdr_loss(y_pred: torch.Tensor, y_true: torch.Tensor,
                max_db: float = 20.0) -> torch.Tensor:
    if y_pred.dim() < 2:
        return y_pred.new_tensor(0.0)

    if y_pred.dim() >= 4:
        y_pred = y_pred.flatten(start_dim=2)
        y_true = y_true.flatten(start_dim=2)
    else:
        y_pred = y_pred.reshape(1, -1, y_pred.shape[-1])
        y_true = y_true.reshape(1, -1, y_true.shape[-1])

    y_pred = y_pred - y_pred.mean(dim=-1, keepdim=True)
    y_true = y_true - y_true.mean(dim=-1, keepdim=True)

    dot = torch.sum(y_pred * y_true, dim=-1, keepdim=True)
    target_energy = torch.sum(y_true ** 2, dim=-1, keepdim=True).clamp_min(1e-8)
    scaled_target = dot * y_true / target_energy
    noise = y_pred - scaled_target

    ratio = torch.sum(scaled_target ** 2, dim=-1) / torch.sum(noise ** 2, dim=-1).clamp_min(1e-8)
    si_sdr = 10.0 * torch.log10(ratio.clamp_min(1e-8))
    si_sdr = si_sdr.clamp(max=max_db)
    return -si_sdr.mean()


def mixture_consistency_loss(y_pred: torch.Tensor, x: Optional[torch.Tensor],
                             stft_weight: float = 0.25) -> torch.Tensor:
    if x is None or y_pred.dim() < 4:
        return y_pred.new_tensor(0.0)

    pred_mix = y_pred.sum(dim=1)
    if pred_mix.shape[-1] != x.shape[-1]:
        n = min(pred_mix.shape[-1], x.shape[-1])
        pred_mix = pred_mix[..., :n]
        x = x[..., :n]

    loss = F.l1_loss(pred_mix, x)
    if stft_weight > 0:
        loss = loss + stft_weight * spectral_convergence_loss(pred_mix, x)
    return loss


def spectral_overlap_loss(y_pred: torch.Tensor,
                          n_fft: int = 2048,
                          hop_length: int = 512,
                          power: float = 1.0) -> torch.Tensor:
    if y_pred.dim() < 4 or y_pred.shape[1] < 2:
        return y_pred.new_tensor(0.0)

    stem_a = y_pred[:, 0].reshape(-1, y_pred.shape[-1])
    stem_b = y_pred[:, 1].reshape(-1, y_pred.shape[-1])
    window = torch.hann_window(n_fft, device=y_pred.device)

    spec_a = torch.stft(
        stem_a, n_fft=n_fft, hop_length=hop_length, window=window,
        return_complex=True
    ).abs()
    spec_b = torch.stft(
        stem_b, n_fft=n_fft, hop_length=hop_length, window=window,
        return_complex=True
    ).abs()

    if power != 1.0:
        spec_a = spec_a.clamp_min(1e-8).pow(power)
        spec_b = spec_b.clamp_min(1e-8).pow(power)

    shared = (spec_a * spec_b) / (spec_a.square() + spec_b.square() + 1e-8)
    energy = (spec_a + spec_b).detach()
    active = energy > torch.quantile(energy.flatten(), 0.25)
    if not torch.any(active):
        return shared.mean()
    return shared[active].mean()


class CompositeProLoss:
    def __init__(self, config: dict):
        if hasattr(config, 'loss'):
            loss_cfg = config.loss
        elif isinstance(config, dict):
            loss_cfg = config.get('loss', {})
        else:
            loss_cfg = {}

        self.weights = {
            'l1_waveform': _cfg_get(loss_cfg, 'l1_waveform_coef', 1.0),
            'multi_stft': _cfg_get(loss_cfg, 'multi_stft_coef', 1.0),
            'spectral_convergence': _cfg_get(loss_cfg, 'spectral_convergence_coef', 0.5),
            'min_energy': _cfg_get(loss_cfg, 'min_energy_coef', 5.0),
            'si_sdr': _cfg_get(loss_cfg, 'si_sdr_coef', 0.02),
            'mixture_consistency': _cfg_get(loss_cfg, 'mixture_consistency_coef', 0.5),
            'spectral_overlap': _cfg_get(loss_cfg, 'spectral_overlap_coef', 0.25),
        }
        self.threshold = _cfg_get(loss_cfg, 'min_energy_threshold', 0.1)
        self.min_target_energy = _cfg_get(loss_cfg, 'min_target_energy', 1e-7)
        self.si_sdr_max_db = _cfg_get(loss_cfg, 'si_sdr_max_db', 20.0)
        self.mixture_stft_weight = _cfg_get(loss_cfg, 'mixture_consistency_stft_weight', 0.25)
        self.overlap_n_fft = _cfg_get(loss_cfg, 'spectral_overlap_n_fft', 2048)
        self.overlap_hop_length = _cfg_get(loss_cfg, 'spectral_overlap_hop_length', 512)
        self.overlap_power = _cfg_get(loss_cfg, 'spectral_overlap_power', 1.0)
        self.flags = {
            'l1_waveform': _cfg_get(loss_cfg, 'l1_waveform', True),
            'multi_stft': _cfg_get(loss_cfg, 'multi_stft', True),
            'spectral_convergence': _cfg_get(loss_cfg, 'spectral_convergence', True),
            'min_energy': _cfg_get(loss_cfg, 'min_energy', True),
            'si_sdr': _cfg_get(loss_cfg, 'si_sdr', True),
            'mixture_consistency': _cfg_get(loss_cfg, 'mixture_consistency', True),
            'spectral_overlap': _cfg_get(loss_cfg, 'spectral_overlap', True),
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
            total += self.weights['min_energy'] * min_energy_loss(
                y_pred, y_true, self.threshold, self.min_target_energy
            )
        if self.flags['si_sdr']:
            total += self.weights['si_sdr'] * si_sdr_loss(y_pred, y_true, self.si_sdr_max_db)
        if self.flags['mixture_consistency']:
            total += self.weights['mixture_consistency'] * mixture_consistency_loss(
                y_pred, x, self.mixture_stft_weight
            )
        if self.flags['spectral_overlap']:
            total += self.weights['spectral_overlap'] * spectral_overlap_loss(
                y_pred, self.overlap_n_fft, self.overlap_hop_length, self.overlap_power
            )
        return total


def choice_loss_pro(config) -> Callable:
    return CompositeProLoss(config)
