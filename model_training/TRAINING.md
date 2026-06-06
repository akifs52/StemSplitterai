# Lead/Rhythm Guitar Separation Training

## Quick Start (v2 — Fixed Pipeline)

### 1. Sanity Check (ilk seferde bir kez çalıştırın)
```powershell
cd D:\qt\stemsplitteraiapp\model_training
python scripts/sanity_check.py --config_path configs/config_leadrhythm_v2.yaml --data_path D:/qt/stemsplitteraiapp/dataset/train_slakh --num_steps 100
```
Loss düşüyorsa pipeline doğru çalışıyor demektir. ✅

### 2. Start Fresh Training (v2 + pro_loss)
```powershell
cd D:\qt\stemsplitteraiapp\model_training
python train_accelerate.py --model_type mel_band_roformer --config_path configs/config_leadrhythm_v2.yaml --results_path results/leadrhythm_v2 --data_path D:/qt/stemsplitteraiapp/dataset/train_slakh --valid_path D:/qt/stemsplitteraiapp/dataset/valid_slakh --dataset_type 1 --num_workers 2 --pin_memory True --seed 42 --valid_every 5 --use_standard_loss --loss pro_loss
```

### 3. Resume from checkpoint (mevcut training'e devam)
```powershell
cd D:\qt\stemsplitteraiapp\model_training
python train_accelerate.py --model_type mel_band_roformer --config_path configs/config_leadrhythm_v2.yaml --results_path results/leadrhythm_v2 --data_path D:/qt/stemsplitteraiapp/dataset/train_slakh --valid_path D:/qt/stemsplitteraiapp/dataset/valid_slakh --dataset_type 1 --num_workers 2 --pin_memory True --seed 42 --valid_every 5 --use_standard_loss --loss pro_loss --resume_from_checkpoint results/leadrhythm_v2/checkpoint
```

---

## pro_loss (Composite Loss) Nedir?

Internal multi-STFT loss modeli iki stem'i de kullanmaya zorlamıyor → model rhythm'i sessize çekip kaçıyordu. `pro_loss` 4 bileşenle bunu engeller:

| Loss | Katsayı | Ne işe yarar |
|------|---------|-------------|
| `l1_waveform` | 1.0 | Temel dalgaformu uyumu |
| `multi_stft` | 1.0 | Çoklu-çözünürlüklü spektral uyum |
| `spectral_convergence` | 0.5 | Frekans spektrumunun genel şeklini zorlar |
| `min_energy` | 2.0 | **Kritik**: output enerjisi input'un %1'inden azsa cezalandırır (sessiz çıkışı engeller) |

### Epoch 0-20 Durumu (pro_loss öncesi)
| Epoch | Lead SDR | Rhythm SDR | Yorum |
|-------|----------|------------|-------|
| 0 | +0.09 | -21.27 | Lead başlangıç iyi, rhythm ihmal edilmiş |
| 10 | -3.68 | -30.58 | Her şey kötüleşti |
| 20 | -4.30 | -31.57 | Model rhythm'i sessize çekmeyi öğrendi |

`min_energy_loss` (coef=2.0) bu durumu engelleyecek.

---

## v1 vs v2 Comparison

| Setting | v1 (Slakh) | v2 (Fixed) | v2 + pro_loss | Reason |
|---------|-----------|------------|---------------|--------|
| LR | 2e-4 | 5e-5 | 5e-5 | v1 too high, model diverged |
| Scheduler | cosine (broken!) | cosine (working) | cosine (working) | v1 always used ReduceLROnPlateau |
| Warmup | 1000 (broken!) | 500 (working) | 500 (working) | Stabilizes early training |
| Loss | internal multi-STFT | internal multi-STFT | **CompositeProLoss** | Prevents silence on one stem |
| Grad accum | 2 (broken!) | 4 (working) | 4 (working) | v1 ignored this setting |
| Effective batch | 2 | 4 | 4 | Better gradient estimates |
| Chunk size | 176128 (~4s) | 264600 (~6s) | 264600 (~6s) | More temporal context |
| Model depth | 3 | 4 | 4 | Deeper = better features |
| Mel bands | 48 | 60 | 60 | Finer frequency resolution |
| Dropout | 0.1 | 0.05 | 0.05 | Less regularization needed |
| Grad clip | 1.0 | 0.5 | 0.5 | Prevent gradient explosion |

## Bug Fixes in train_accelerate.py (v1.1.0)

1. **Gradient accumulation**: Now reads `gradient_accumulation_steps` from config
2. **Cosine scheduler**: Now reads `scheduler` from config (was hardcoded ReduceLROnPlateau)
3. **Warmup**: Now reads `num_warmup_steps` from config
4. **Custom loss**: Added `--use_standard_loss` and `--loss` flags
5. **Better logging**: Shows LR in progress bar and epoch summary

## Notes
- `--valid_every 5`: validation runs every 5 epochs (~2.5h each)
- Model: dim=128, depth=4, 60 mel bands, ~65M params, 44.1 kHz, 6s chunks
- Dataset: 1286 train + 270 valid tracks from Slakh2100
- Checkpoints: `results/leadrhythm_v2/checkpoint/` (full state, every epoch)
- Best SDR checkpoints: `results/leadrhythm_v2/model_mel_band_roformer_ep_*_sdr_*.ckpt`
- Resume: `--use_standard_loss --loss pro_loss` parametreleri resume'da da aynen verilmelidir
