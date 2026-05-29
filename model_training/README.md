# Music Source Separation Universal Training Code

Repository for training models for music source separation. Repository is based on [kuielab code](https://github.com/kuielab/sdx23/tree/mdx_AB/my_submission/src) for [SDX23 challenge](https://github.com/kuielab/sdx23/tree/mdx_AB/my_submission/src). The main idea of this repository is to create training code, which is easy to modify for experiments. Brought to you by [MVSep.com](https://mvsep.com).

---

## Lead/Rhythm Guitar Separation Pipeline

Custom pipeline built on top of ZFTurbo for professional-quality lead/rhythm guitar separation using MelBand-RoFormer architecture.

**Target**: Separate mixed guitar stems (from HTDemucs) into clean `lead_guitar` and `rhythm_guitar` tracks.

### Key Features

| Feature | Description |
|---------|-------------|
| **Architecture** | MelBand-RoFormer (dim=192, depth=4, heads=6, 101M params) |
| **Loss Function** | 7-loss composite: L1 + Multi-resolution STFT + Spectral Convergence + SI-SDR + Stem Leakage Penalty + Stereo Consistency + Center-Aware Lead |
| **Augmentations** | 10 phase-coherent augs: gain, stereo width, EQ, cabinet coloration, saturation, reverb, panning, MS rotation, time masking, freq masking |
| **Post-Processing** | Optional DSP: transient enhancement, harmonic enhancement, spectral denoising, stereo restoration |
| **Inference** | Chunked overlap-add with Wiener refinement + Hann window blending |
| **Curriculum** | Difficulty-based curriculum learning (easy→hard) |
| **Hardware** | Optimized for RTX 3050 Ti 4GB (batch_size=2, chunk_size=176128, mixed precision) |

### New Files

| File | Purpose |
|------|---------|
| `configs/config_leadrhythm_pro.yaml` | Professional training config (AdamW, lr=3e-4, warmup=1000, cosine scheduler, grad_clip=1.0) |
| `utils/losses_pro.py` | Composite loss: `l1_waveform_loss`, `multi_resolution_stft_loss`, `spectral_convergence_loss`, `si_sdr_loss`, `stem_leakage_loss`, `stereo_consistency_loss`, `center_aware_lead_loss` |
| `utils/augs_pro.py` | `GuitarAugmentationPipeline` — 10 phase-coherent augmentations per-stem |
| `utils/post_pro.py` | DSP post-processing: `transient_enhance`, `harmonic_enhance`, `spectral_denoise`, `stereo_restore` |
| `utils/curriculum.py` | `CurriculumSampler` — epoch-based difficulty progression |
| `inference_pro.py` | Chunked inference + Wiener refinement + optional DSP post-processing |

### Loss Functions Detail

The composite `pro_loss` combines 7 terms with configurable weights:

- **L1 Waveform** (weight=1.0): Basic time-domain amplitude error
- **Multi-Resolution STFT** (weight=1.0): L1 on STFT magnitudes across 5 window sizes (4096, 2048, 1024, 512, 256)
- **Spectral Convergence** (weight=0.5): `||STFT(pred) - STFT(true)||_F / ||STFT(true)||_F`
- **SI-SDR** (weight=0.1): Scale-invariant SDR (negated as loss)
- **Stem Leakage Penalty** (weight=0.3): `mean(|lead_pred| * |rhythm_true|) + mean(|rhythm_pred| * |lead_true|)` in spectrogram domain — penalizes cross-stem energy bleed
- **Stereo Consistency** (weight=0.2): L1 on inter-channel correlation difference between prediction and target
- **Center-Aware Lead** (weight=0.4): Mid-side weighted L1 (mid weight=1.5x, side weight=0.5x) — emphasizes center-panned lead guitar

### Training

```bash
# Fresh training
python train.py \
    --model_type mel_band_roformer \
    --config_path configs/config_leadrhythm_pro.yaml \
    --results_path results/leadrhythm_v2 \
    --data_path ../dataset/train \
    --valid_path ../dataset/valid \
    --dataset_type 1 \
    --num_workers 2 \
    --device_ids 0 \
    --loss pro_loss \
    --use_standard_loss \
    --save_weights_every_epoch

# Resume from checkpoint
python train.py \
    --model_type mel_band_roformer \
    --config_path configs/config_leadrhythm_pro.yaml \
    --results_path results/leadrhythm_v2 \
    --data_path ../dataset/train \
    --valid_path ../dataset/valid \
    --dataset_type 1 \
    --num_workers 2 \
    --device_ids 0 \
    --loss pro_loss \
    --use_standard_loss \
    --save_weights_every_epoch \
    --start_check_point results/leadrhythm_v2/last_mel_band_roformer.ckpt \
    --load_optimizer --load_scheduler --load_epoch --load_best_metric

# Or use the batch script
train_leadrhythm.bat
```

### Inference

```bash
# Basic inference
python inference_pro.py \
    --config_path configs/config_leadrhythm_pro.yaml \
    --checkpoint results/leadrhythm_v2/last_mel_band_roformer.ckpt \
    --input path/to/song.wav \
    --output separated/

# Inference with Wiener refinement and DSP post-processing
python inference_pro.py \
    --config_path configs/config_leadrhythm_pro.yaml \
    --checkpoint results/leadrhythm_v2/last_mel_band_roformer.ckpt \
    --input path/to/songs_folder/ \
    --output separated/ \
    --overlap 4 \
    --wiener \
    --post_process
```

### Dataset Format (Type 1)

Each track is a folder containing:
```
track_name/
├── mixture.wav        # Mixed guitar stem
├── lead_guitar.wav    # Target: lead guitar
└── rhythm_guitar.wav  # Target: rhythm guitar
```

### Augmentation Pipeline

10 augmentations applied per-stem before mixing, all designed to preserve phase coherence:

| Augmentation | Range | Phase-Safe |
|---|---|---|
| Random Gain | [0.7, 1.3] | ✅ scalar |
| Stereo Width | [0.5, 1.5] | ✅ linear MS |
| 7-Band EQ | [-6, +6] dB | ✅ linear filter |
| Cabinet Filter | HPF 80-200Hz + LPF 4-8kHz | ✅ linear filter |
| Saturation | drive [0, 0.3] | ⚠️ minimal |
| Room Reverb | wet [0, 0.15] | ⚠️ minimal |
| Random Panning | [0.8, 1.0] | ✅ linear |
| MS Rotation | ±15° | ✅ orthogonal |
| Time Masking | [0.05s, 0.3s] | ✅ zero gaps |
| Freq Masking | 1-3 bands | ✅ zero bands |

---

## Models

Model can be chosen with `--model_type` arg.

Available models for training:

* MDX23C based on [KUIELab TFC TDF v3 architecture](https://github.com/kuielab/sdx23/). Key: `mdx23c`.
* Demucs4HT [[Paper](https://arxiv.org/abs/2211.08553)]. Key: `htdemucs`.
* VitLarge23 based on [Segmentation Models Pytorch](https://github.com/qubvel/segmentation_models.pytorch). Key: `segm_models`.
* TorchSeg based on [TorchSeg module](https://github.com/qubvel/segmentation_models.pytorch). Key: `torchseg`.
* Band Split RoFormer [[Paper](https://arxiv.org/abs/2309.02612), [Repository](https://github.com/lucidrains/BS-RoFormer)] . Key: `bs_roformer`.
* Mel-Band RoFormer [[Paper](https://arxiv.org/abs/2310.01809), [Repository](https://github.com/lucidrains/BS-RoFormer)]. Key: `mel_band_roformer`.
* Swin Upernet [[Paper](https://arxiv.org/abs/2103.14030)] Key: `swin_upernet`.
* BandIt Plus [[Paper](https://arxiv.org/abs/2309.02539), [Repository](https://github.com/karnwatcharasupat/bandit)] Key: `bandit`.
* SCNet [[Paper](https://arxiv.org/abs/2401.13276), [Official Repository](https://github.com/starrytong/SCNet), [Unofficial Repository](https://github.com/amanteur/SCNet-PyTorch)] Key: `scnet`.
* BandIt v2 [[Paper](https://arxiv.org/abs/2407.07275), [Repository](https://github.com/kwatcharasupat/bandit-v2)] Key: `bandit_v2`.
* Apollo [[Paper](https://arxiv.org/html/2409.08514v1), [Repository](https://github.com/JusperLee/Apollo)] Key: `apollo`.
* BSMamba2 [[Paper](https://arxiv.org/abs/2508.14556), [Repository](https://github.com/EuiYeonKim/BSMamba2)] Key: `bs_mamba2`.
* Conformer [[Paper](https://arxiv.org/abs/2005.08100), [Repository](https://github.com/lucidrains/conformer)] Key: `conformer`.
* BS Conformer Key: `bs_conformer`
* SCNet Tran Key: `scnet_tran`.
* SCNet Masked Key: `scnet_masked`.

1. **Note 1**: For `segm_models` there are many different encoders is possible. [Look here](https://github.com/qubvel/segmentation_models.pytorch#encoders-).
2. **Note 2**: Thanks to [@lucidrains](https://github.com/lucidrains) for recreating the RoFormer models based on papers.
3. **Note 3**: For `torchseg` gives access to more than 800 encoders from `timm` module. It's similar to `segm_models`.

## How to: Train

To train model you need to:

1) Choose model type with option `--model_type`, including: `mdx23c`, `htdemucs`, `segm_models`, `mel_band_roformer`, `bs_roformer`.
2) Choose location of config for model `--config_path` `<config path>`. You can find examples of configs in [configs folder](configs/). Prefixes `config_musdb18_` are examples for [MUSDB18 dataset](https://sigsep.github.io/datasets/musdb.html).
3) If you have a check-point from the same model or from another similar model you can use it with option: `--start_check_point` `<weights path>`
4) Choose path where to store results of training `--results_path` `<results folder path>`

### Training example

```bash
python train.py \
    --model_type mel_band_roformer \
    --config_path configs/config_mel_band_roformer_vocals.yaml \
    --start_check_point results/model.ckpt \
    --results_path results/ \
    --data_path 'datasets/dataset1' 'datasets/dataset2' \
    --valid_path datasets/musdb18hq/test \
    --num_workers 4 \
    --device_ids 0
```

All training parameters are [here](https://github.com/ZFTurbo/Music-Source-Separation-Training/blob/main/utils/settings.py#L20).

### Training with LoRA

Look here: [LoRA training](docs/LoRA.md)

## How to: Inference

### Inference example

```bash
python inference.py \
    --model_type mdx23c \
    --config_path configs/config_mdx23c_musdb18.yaml \
    --start_check_point results/last_mdx23c.ckpt \
    --input_folder input/wavs/ \
    --store_dir separation_results/
```

All inference parameters are [here](https://github.com/ZFTurbo/Music-Source-Separation-Training/blob/main/utils/settings.py#L130).
Convert models to ONNX and TensorRT formats [here](https://github.com/ZFTurbo/MSS_ONNX_TensorRT).

## Useful notes

* All batch sizes in config are adjusted to use with single NVIDIA A6000 48GB. If you have less memory please adjust correspodningly in model config `training.batch_size` and `training.gradient_accumulation_steps`.
* It's usually always better to start with old weights even if shapes not fully match. Code supports loading weights for not fully same models (but it must have the same architecture). Training will be much faster.

## Code description

* `configs/config_*.yaml` - configuration files for models
* `configs/config_leadrhythm_pro.yaml` - professional lead/rhythm guitar training config
* `models/*` - set of available models for training and inference
* `dataset.py` - dataset which creates new samples for training
* `gui-wx.py` - GUI interface for code
* `inference.py` - process folder with music files and separate them
* `inference_pro.py` - professional lead/rhythm inference with Wiener refinement + DSP post-processing
* `train.py` - main training code for single GPU
* `train_ddp.py` - training code for Multi GPU config. Faster than `train.py`. Use it for 2 or more GPUs.
* `train_leadrhythm.bat` - batch script for lead/rhythm training (fresh start or resume)
* `utils.py` - common functions used by train/valid
* `valid.py` - validation of model with metrics
* `ensemble.py` - useful script to ensemble results of different models to make results better (see [docs](docs/ensemble.md)).   
* `utils/losses_pro.py` - 7-loss composite for guitar separation (L1, STFT, SI-SDR, leakage, stereo, etc.)
* `utils/augs_pro.py` - 10 phase-coherent guitar-specific augmentations
* `utils/post_pro.py` - DSP post-processing (transient, harmonic, denoise, stereo restore)
* `utils/curriculum.py` - difficulty-based curriculum sampler

## Pre-trained models

Look here: [List of Pre-trained models](docs/pretrained_models.md)

If you trained some good models, please, share them. You can post config and model weights [in this issue](https://github.com/ZFTurbo/Music-Source-Separation-Training/issues/1).

## Dataset types

Look here: [Dataset types](docs/dataset_types.md)

## Augmentations

Look here: [Augmentations](docs/augmentations.md)

## Graphical user interface

Look here: [GUI documentation](docs/gui.md) or see tutorial on [Youtube](https://youtu.be/M8JKFeN7HfU)

## Citation

* [arxiv paper](https://arxiv.org/abs/2305.07489)

```text
@misc{solovyev2023benchmarks,
      title={Benchmarks and leaderboards for sound demixing tasks}, 
      author={Roman Solovyev and Alexander Stempkovskiy and Tatiana Habruseva},
      year={2023},
      eprint={2305.07489},
      archivePrefix={arXiv},
      primaryClass={cs.SD}
}
```
