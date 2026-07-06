import os
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from backend.process_utils import ffmpeg_program, popen_hidden, run_hidden
from backend.progress_parser import ProgressParser
from backend.waveform import compute_waveform
from saas.core.security import utcnow
from saas.db.mongo import get_event_store
from saas.db.postgres import SessionLocal
from saas.models import Job, JobArtifact
from saas.services.storage import content_type_for, get_storage_service, object_key


def _set_job(db: Session, job: Job, **values) -> None:
    for key, value in values.items():
        setattr(job, key, value)
    job.updated_at = utcnow()
    db.commit()


def _conversion_args(src_path: Path, dst_path: Path) -> list[str]:
    ext = dst_path.suffix.lower()
    args = [ffmpeg_program(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src_path), "-vn"]
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


def _convert_if_needed(src_path: Path, target_ext: str) -> Path:
    if target_ext == ".wav":
        return src_path
    dst_path = src_path.with_suffix(target_ext)
    run_hidden(_conversion_args(src_path, dst_path), capture_output=True, text=True, check=True)
    return dst_path


def _collect_stems(stem_dir: Path, target_ext: str) -> list[Path]:
    stems = []
    for path in sorted(stem_dir.iterdir()) if stem_dir.is_dir() else []:
        if not path.is_file() or path.suffix.lower() not in {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}:
            continue
        if path.suffix.lower() != target_ext and (stem_dir / f"{path.stem}{target_ext}").exists():
            continue
        stems.append(path)
    return stems


def _has_cuda() -> bool:
    try:
        from backend.cuda_checker import has_cuda

        return bool(has_cuda())
    except Exception:
        return False


def process_job(job_id: str) -> None:
    db = SessionLocal()
    event_store = get_event_store()
    storage = get_storage_service()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        if job.cancel_requested:
            _set_job(db, job, status="cancelled", stage="Cancelled before start", progress=0, completed_at=utcnow())
            event_store.append_event(job_id, "cancelled", {"stage": "before_start"})
            return

        _set_job(db, job, status="running", stage="Preparing", progress=1, started_at=utcnow())
        event_store.append_event(job_id, "started", {"model": job.model})

        with tempfile.TemporaryDirectory(prefix=f"stemsplit-{job_id}-") as tmp_dir_raw:
            tmp_dir = Path(tmp_dir_raw)
            source_path = tmp_dir / job.source_filename
            output_dir = tmp_dir / "separated"
            output_dir.mkdir(parents=True, exist_ok=True)
            storage.download_to_path(job.source_object_key, source_path)

            target_ext = source_path.suffix.lower() or ".wav"
            stem_dir = output_dir / job.model / source_path.stem
            parser = ProgressParser()
            log_lines: list[str] = []
            args = [
                sys.executable or "python",
                "-m",
                "demucs",
                "-n",
                job.model,
                "-o",
                str(output_dir),
                "--segment",
                str(job.segment),
                "--overlap",
                str(job.overlap),
                "--shifts",
                str(job.shifts),
                "--device",
                "cuda" if _has_cuda() else "cpu",
                str(source_path),
            ]

            process = popen_hidden(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in process.stdout:
                db.refresh(job)
                if job.cancel_requested:
                    process.kill()
                    _set_job(db, job, status="cancelled", stage="Cancelled", progress=0, completed_at=utcnow())
                    event_store.append_event(job_id, "cancelled", {"stage": job.stage})
                    return
                line = line.strip()
                if not line:
                    continue
                log_lines.append(line)
                if len(log_lines) > 100:
                    log_lines = log_lines[-100:]
                event_store.append_log(job_id, line)
                progress, stage = parser.parse_line(line)
                _set_job(db, job, stage=stage, progress=min(progress, 99))

            code = process.wait()
            if code != 0:
                detail = "\n".join(log_lines[-12:]).strip()
                message = f"Demucs failed ({code})"
                if detail:
                    message = f"{message}: {detail}"
                _set_job(db, job, status="error", stage=message[:512], error_message=message, completed_at=utcnow())
                event_store.append_event(job_id, "error", {"message": message})
                return

            if target_ext != ".wav":
                _set_job(db, job, stage=f"Converting stems to {target_ext[1:].upper()}...", progress=98)
                for wav_path in sorted(stem_dir.glob("*.wav")):
                    _convert_if_needed(wav_path, target_ext)

            stems = _collect_stems(stem_dir, target_ext)
            stem_waveforms = {}
            for stem_path in stems:
                artifact_key = object_key(
                    "organizations",
                    job.organization_id,
                    "jobs",
                    job.id,
                    "stems",
                    stem_path.name,
                )
                storage.put_path(stem_path, artifact_key, content_type_for(stem_path.name, "audio/wav"))
                artifact = JobArtifact(
                    job_id=job.id,
                    name=stem_path.stem,
                    object_key=artifact_key,
                    content_type=content_type_for(stem_path.name, "audio/wav"),
                    size_bytes=os.path.getsize(stem_path),
                )
                db.add(artifact)
                try:
                    stem_waveforms[stem_path.stem] = compute_waveform(str(stem_path), max_points=360)
                except Exception:
                    stem_waveforms[stem_path.stem] = []

            try:
                original_waveform = compute_waveform(str(source_path))
            except Exception:
                original_waveform = []
            event_store.save_waveform(job.id, original_waveform, stem_waveforms)
            _set_job(db, job, status="done", stage="Complete!", progress=100, completed_at=utcnow())
            event_store.append_event(job_id, "done", {"artifact_count": len(stems)})
    except Exception as exc:
        job = db.get(Job, job_id)
        if job is not None:
            _set_job(db, job, status="error", stage=str(exc)[:512], error_message=str(exc), completed_at=utcnow())
        event_store.append_event(job_id, "error", {"message": str(exc)})
        raise
    finally:
        db.close()


def worker_main() -> None:
    from redis import Redis
    from rq import Worker

    from saas.core.config import get_settings

    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker([settings.rq_queue_name], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    worker_main()

