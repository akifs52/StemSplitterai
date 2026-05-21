import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.cuda_checker import has_cuda
from backend.progress_parser import ProgressParser
from backend.waveform import compute_waveform


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "separated" / "web"
STATIC_DIR = BASE_DIR / "web" / "static"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="StemSplit AI Web")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")

jobs = {}
jobs_lock = threading.Lock()


def _set_job(job_id, **values):
    with jobs_lock:
        job = jobs[job_id]
        job.update(values)
        return dict(job)


def _safe_name(name):
    stem = Path(name).stem.strip() or "audio"
    return "".join(ch if ch.isalnum() or ch in " ._-" else "_" for ch in stem).strip()


def _conversion_args(src_path, dst_path):
    ext = Path(dst_path).suffix.lower()
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src_path), "-vn"]
    if ext == ".mp3":
        args += ["-codec:a", "libmp3lame", "-q:a", "2"]
    elif ext == ".flac":
        args += ["-codec:a", "flac"]
    elif ext == ".ogg":
        args += ["-codec:a", "libvorbis", "-q:a", "6"]
    elif ext in (".m4a", ".aac"):
        args += ["-codec:a", "aac", "-b:a", "256k"]
    args.append(str(dst_path))
    return args


def _convert_if_needed(src_path, target_ext):
    if target_ext == ".wav":
        return src_path
    dst_path = src_path.with_suffix(target_ext)
    subprocess.run(_conversion_args(src_path, dst_path), capture_output=True, text=True, check=True)
    return dst_path


def _collect_stems(stem_dir, target_ext):
    stems = []
    for path in sorted(stem_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}:
            continue
        if path.suffix.lower() != target_ext and (stem_dir / f"{path.stem}{target_ext}").exists():
            continue
        stems.append({"name": path.stem, "path": str(path)})
    return stems


def _run_split(job_id):
    with jobs_lock:
        job = jobs[job_id]
        source_path = Path(job["source_path"])
        model = job["model"]
        segment = job["segment"]
        overlap = job["overlap"]
        shifts = job["shifts"]

    parser = ProgressParser()
    log_lines = []
    base_name = source_path.stem
    target_ext = source_path.suffix.lower() or ".wav"
    job_out = OUTPUT_DIR / job_id
    stem_dir = job_out / model / base_name
    job_out.mkdir(parents=True, exist_ok=True)

    args = [
        sys.executable or "python",
        "-m",
        "demucs",
        "-n",
        model,
        "-o",
        str(job_out),
        "--segment",
        str(segment),
        "--overlap",
        str(overlap),
        "--shifts",
        str(shifts),
        "--device",
        "cuda" if has_cuda() else "cpu",
        str(source_path),
    ]

    _set_job(job_id, status="running", stage=model, progress=1)
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _set_job(job_id, pid=process.pid)

    try:
        for line in process.stdout:
            with jobs_lock:
                if jobs[job_id].get("cancel_requested"):
                    process.kill()
                    _set_job(job_id, status="cancelled", stage="Cancelled", progress=0)
                    return
            line = line.strip()
            if not line:
                continue
            log_lines.append(line)
            if len(log_lines) > 80:
                log_lines = log_lines[-80:]
            progress, status = parser.parse_line(line)
            _set_job(job_id, stage=status, progress=min(progress, 99))

        code = process.wait()
        if code != 0:
            detail = "\n".join(log_lines[-12:]).strip()
            message = f"Demucs failed ({code})"
            if detail:
                message = f"{message}: {detail}"
            _set_job(job_id, status="error", stage=message, error_log="\n".join(log_lines))
            return

        if target_ext != ".wav":
            _set_job(job_id, stage=f"Converting stems to {target_ext[1:].upper()}...", progress=98)
            for wav_path in sorted(stem_dir.glob("*.wav")):
                _convert_if_needed(wav_path, target_ext)

        stems = _collect_stems(stem_dir, target_ext)
        original_waveform = compute_waveform(str(source_path))
        stem_waveforms = {stem["name"]: compute_waveform(stem["path"], max_points=360) for stem in stems}
        _set_job(
            job_id,
            status="done",
            stage="Complete!",
            progress=100,
            stems=stems,
            waveform=original_waveform,
            stem_waveforms=stem_waveforms,
        )
    except Exception as exc:
        _set_job(job_id, status="error", stage=str(exc))


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    model: str = Form("htdemucs"),
    segment: int = Form(10),
    overlap: float = Form(0.25),
    shifts: int = Form(1),
):
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    job_id = uuid.uuid4().hex
    source_path = UPLOAD_DIR / f"{job_id}{suffix}"
    with source_path.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)

    jobs[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "source_path": str(source_path),
        "model": model,
        "segment": segment,
        "overlap": overlap,
        "shifts": shifts,
        "status": "queued",
        "stage": "Queued",
        "progress": 0,
        "created_at": time.time(),
        "stems": [],
        "waveform": [],
        "stem_waveforms": {},
        "error_log": "",
        "cancel_requested": False,
    }
    thread = threading.Thread(target=_run_split, args=(job_id,), daemon=True)
    thread.start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        public = dict(job)
    public.pop("source_path", None)
    public.pop("pid", None)
    return public


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        jobs[job_id]["cancel_requested"] = True
    return {"ok": True}


@app.get("/api/jobs/{job_id}/download/{stem_name}")
def download_stem(job_id: str, stem_name: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        stems = list(job.get("stems", []))
    stem = next((item for item in stems if item["name"] == stem_name), None)
    if not stem or not os.path.isfile(stem["path"]):
        raise HTTPException(status_code=404, detail="Stem not found")
    return FileResponse(stem["path"], filename=os.path.basename(stem["path"]))


@app.get("/api/system")
def system_info():
    return {"gpu": has_cuda(), "device": "CUDA" if has_cuda() else "CPU"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
