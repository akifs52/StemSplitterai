# -*- mode: python ; coding: utf-8 -*-

import os
import shutil
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

numpy_datas, numpy_binaries, numpy_hidden = collect_all('numpy')
torch_binaries = collect_dynamic_libs('torch')
torchaudio_binaries = collect_dynamic_libs('torchaudio')
demucs_datas = collect_data_files('demucs')
demucs_hidden = collect_submodules('demucs')


def collect_ffmpeg():
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        return []

    ffmpeg_dir = os.path.dirname(ffmpeg)
    binaries = [(ffmpeg, 'bin')]
    for name in os.listdir(ffmpeg_dir):
        lower = name.lower()
        if lower.endswith('.dll') or lower in ('ffprobe.exe', 'ffplay.exe'):
            binaries.append((os.path.join(ffmpeg_dir, name), 'bin'))
    return binaries


ffmpeg_binaries = collect_ffmpeg()

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=numpy_binaries + torch_binaries + torchaudio_binaries + ffmpeg_binaries,
    datas=[
        ('assets', 'assets'),
        ('qml', 'qml'),
    ] + numpy_datas + demucs_datas,
    hiddenimports=[
        'backend',
        'backend.audio_player',
        'backend.backend_controller',
        'backend.cache_manager',
        'backend.cuda_checker',
        'backend.database',
        'backend.progress_parser',
        'backend.splitter',
        'backend.waveform',
        'backend.worker',
        'demucs',
        'demucs.separate',
        'torch',
        'torchaudio',
    ] + numpy_hidden + demucs_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'cv2',
        'notebook',
        'jupyter',
        'pandas',
        'scipy',
        'numba',
        'onnxruntime',
        'tensorflow',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StemSplitAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime*.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('assets', 'icons', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime*.dll'],
    name='StemSplitAI',
)
