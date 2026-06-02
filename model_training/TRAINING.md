# Lead/Rhythm Guitar Separation Training

## Start training
```powershell
cd D:\qt\stemsplitteraiapp\model_training
python train_accelerate.py --model_type mel_band_roformer --config_path configs/config_leadrhythm_slakh.yaml --results_path results/leadrhythm_slakh --data_path D:/qt/stemsplitteraiapp/dataset/train_slakh --valid_path D:/qt/stemsplitteraiapp/dataset/valid_slakh --dataset_type 1 --num_workers 2 --pin_memory True --seed 42 --valid_every 5
```

## Resume from checkpoint
```powershell
cd D:\qt\stemsplitteraiapp\model_training
python train_accelerate.py --model_type mel_band_roformer --config_path configs/config_leadrhythm_slakh.yaml --results_path results/leadrhythm_slakh --data_path D:/qt/stemsplitteraiapp/dataset/train_slakh --valid_path D:/qt/stemsplitteraiapp/dataset/valid_slakh --dataset_type 1 --num_workers 2 --pin_memory True --seed 42 --valid_every 5 --resume_from_checkpoint results/leadrhythm_slakh/checkpoint
```

## Notes
- `--valid_every 5`: validation runs every 5 epochs (270 full tracks, ~2.5 saat)
- Resume saves/loads model + optimizer + scheduler + epoch + EMA state fully
- Model: dim=128, depth=3 (50.8M params), 44.1 kHz, 4s chunks
- Dataset: 1286 train + 270 valid tracks from Slakh2100
- Checkpoints: `results/leadrhythm_slakh/last_mel_band_roformer.ckpt` (her epoch)
- Best SDR checkpoints: `results/leadrhythm_slakh/model_mel_band_roformer_ep_*_sdr_*.ckpt`
