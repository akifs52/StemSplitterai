# StemSplit AI

AI-powered audio stem separation desktop app built with **PySide6** (Qt6) + **Demucs**.

## Features

- **Drag-and-drop** audio file import (MP3, WAV, FLAC, OGG up to 500MB)
- **Demucs** AI model for high-quality stem separation
- Model selection: `htdemucs`, `htdemucs_ft`, `htdemucs_6s`, `mdx_extra`
- Adjustable **segment size**, **overlap**, and **shifts** (quality multiplier)
- CUDA GPU acceleration with real-time telemetry (VRAM, GPU load)
- Stem mixer with per-stem mute, solo, gain, and export
- Recent history with database persistence

## Requirements

- Python 3.10+
- PyTorch (with CUDA optional)
- FFmpeg (required by Demucs)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Web App

Run the FastAPI web version locally:

```bash
pip install -r requirements-web.txt
python -m uvicorn web_app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Docker Web App

Build and run the web app with Docker:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000`.

The compose file mounts `uploads/` and `separated/` so uploaded files and generated stems persist on the host.

## Project Structure

```
├── backend/
│   ├── backend_controller.py   # QML-facing API
│   ├── splitter.py             # SplitWorker + Splitter (Demucs orchestration)
│   ├── audio_player.py         # Stem playback engine
│   ├── cuda_checker.py         # CUDA availability detection
│   ├── database.py             # SQLite history
│   ├── cache_manager.py        # MD5-based result caching
│   ├── waveform.py             # Waveform envelope extraction
│   └── progress_parser.py      # Demucs stdout parser
├── qml/
│   ├── Main.qml                # Main window (all UI sections)
│   └── components/
│       ├── TopBar.qml
│       ├── DropZone.qml
│       ├── StemTrack.qml
│       ├── WavePanel.qml
│       ├── ModernSlider.qml
│       ├── ModernCombo.qml
│       └── GlassCard.qml
├── assets/
├── main.py                     # Entry point
└── requirements.txt
```
