# SonicSplit AI

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

Run the full SaaS web stack locally with Docker Compose:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000`.

The web UI is a React + TypeScript + Vite PWA. Source lives in `frontend/`, and production build output is written to `web/static/` so FastAPI can serve it from the same origin.

Frontend development commands:

```bash
cd frontend
npm ci
npm run typecheck
npm run build
npm run dev
```

The PWA caches the app shell, fonts, icons, and static JS/CSS bundles. API calls and audio downloads are intentionally network-only so job progress and secured stem files do not become stale.

## Docker Web App

Build and run the SaaS web app with Docker:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000`.

The compose stack starts the API, worker, PostgreSQL, MongoDB, Redis, and MinIO. The API runs Alembic migrations at startup and the worker consumes Redis/RQ jobs for Demucs processing.

Local MinIO console is available at `http://127.0.0.1:9001` with:

```text
user: stemsplit
password: stemsplit-secret
```

## SaaS API

The SaaS REST API lives under `/api/v1`:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"demo@example.com\",\"password\":\"very-secret-password\",\"organization_name\":\"Demo Studio\"}"
```

Use the returned bearer token for job endpoints:

```bash
curl http://127.0.0.1:8000/api/v1/jobs \
  -H "Authorization: Bearer <token>"
```

Core services:

- PostgreSQL: users, organizations, plans, quota, jobs, artifacts, API tokens
- MongoDB: job events, worker logs, waveform metadata
- Redis/RQ: long-running separation job queue
- MinIO/S3: uploaded audio and generated stems

Legacy `/api/jobs` and `/api/system` routes remain available in non-production mode so the existing web UI can still run locally. Set `STEM_LEGACY_COMPAT_ENABLED=false` in production.

## OAuth Login

Google and Apple login buttons are shown on the auth screen. They become active when the matching provider environment variables are configured.

Google:

```bash
STEM_PUBLIC_BASE_URL=https://your-domain.example
STEM_GOOGLE_CLIENT_ID=...
STEM_GOOGLE_CLIENT_SECRET=...
```

Google redirect URI:

```text
https://your-domain.example/api/v1/auth/oauth/google/callback
```

Apple:

```bash
STEM_PUBLIC_BASE_URL=https://your-domain.example
STEM_APPLE_CLIENT_ID=...
STEM_APPLE_TEAM_ID=...
STEM_APPLE_KEY_ID=...
STEM_APPLE_PRIVATE_KEY_PATH=/run/secrets/apple-auth-key.p8
```

You can use `STEM_APPLE_PRIVATE_KEY` instead of `STEM_APPLE_PRIVATE_KEY_PATH`; replace newlines with `\n` when storing it in a single environment variable.

Apple redirect URI:

```text
https://your-domain.example/api/v1/auth/oauth/apple/callback
```

OAuth callback returns the app token in a URL fragment and the React app stores it in `localStorage`. Provider id tokens are verified server-side before user creation or account linking.

Run migrations manually:

```bash
alembic upgrade head
```

Run API tests:

```bash
python -m pytest -q tests/test_saas_api.py
```

## Project Structure

SaaS additions live in `saas/`, frontend source in `frontend/`, PostgreSQL migrations in `alembic/`, API tests in `tests/`, and CI/CD in `.github/workflows/`.

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

## Build & Release

To create a standalone executable setup file for Windows, follow these steps:

### Method A: Command Line
If you have already built the PyInstaller distribution, you can directly run the Inno Setup Compiler:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\stemsplitai.iss
```

### Method B: Automatic Build Script
This method runs PyInstaller, creates the Inno Setup installer, and generates the `latest.json` for the auto-update system.

First, build the executable with PyInstaller:
```bash
pyinstaller StemSplitAI.spec --noconfirm
```

Then, run the build script to generate the setup and update manifest:
```bash
python scripts\build_release.py --skip-pyinstaller
```
