@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set CONFIG=configs\config_leadrhythm.yaml
set RESULTS=results\leadrhythm_v1
set DATA=..\dataset\train
set VALID=..\dataset\valid
set MODEL=mel_band_roformer

if "%1"=="--continue" (
    :: Find latest checkpoint
    set CKPT=
    for /f "tokens=*" %%f in ('dir /b /o-d "%RESULTS%\*.ckpt" 2^>nul') do (
        if not defined CKPT set CKPT=%RESULTS%\%%f
    )
    if not defined CKPT (
        echo No checkpoint found in %RESULTS%!
        exit /b 1
    )
    echo Continuing from: !CKPT!
    python train.py ^
        --model_type %MODEL% ^
        --config_path %CONFIG% ^
        --results_path %RESULTS% ^
        --data_path %DATA% ^
        --valid_path %VALID% ^
        --dataset_type 1 ^
        --num_workers 2 ^
        --device_ids 0 ^
        --loss l1_snr_loss ^
        --save_weights_every_epoch ^
        --start_check_point "!CKPT!" ^
        --load_optimizer --load_scheduler --load_epoch --load_best_metric
) else (
    python train.py ^
        --model_type %MODEL% ^
        --config_path %CONFIG% ^
        --results_path %RESULTS% ^
        --data_path %DATA% ^
        --valid_path %VALID% ^
        --dataset_type 1 ^
        --num_workers 2 ^
        --device_ids 0 ^
        --loss l1_snr_loss ^
        --save_weights_every_epoch
)
