from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from saas.core.security import utcnow
from saas.db.mongo import get_event_store
from saas.dependencies import AuthContext
from saas.models import Job, JobArtifact, Organization, Plan, UsageLedger
from saas.services.queue import enqueue_split_job
from saas.services.storage import content_type_for, file_size, get_storage_service, object_key


def _month_start() -> datetime:
    now = utcnow()
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _current_plan(db: Session, organization: Organization) -> Plan:
    plan = db.get(Plan, organization.plan_id)
    if plan is None:
        plan = db.get(Plan, "free")
    if plan is None:
        raise HTTPException(status_code=500, detail="Default plan is not configured")
    return plan


def _assert_quota(db: Session, context: AuthContext, upload_size: int) -> None:
    plan = _current_plan(db, context.organization)
    max_bytes = plan.max_upload_mb * 1024 * 1024
    if upload_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Upload exceeds plan limit of {plan.max_upload_mb}MB",
        )
    count = (
        db.query(Job)
        .filter(Job.organization_id == context.organization.id, Job.created_at >= _month_start())
        .count()
    )
    if count >= plan.monthly_job_limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Monthly job quota exceeded")


def _safe_filename(name: str | None) -> str:
    candidate = Path(name or "audio.wav").name
    cleaned = "".join(ch if ch.isalnum() or ch in " ._-" else "_" for ch in candidate).strip()
    return cleaned or "audio.wav"


def create_job(
    db: Session,
    context: AuthContext,
    file: UploadFile,
    model: str,
    segment: int,
    overlap: float,
    shifts: int,
) -> Job:
    size = file_size(file.file)
    file.file.seek(0)
    _assert_quota(db, context, size)

    filename = _safe_filename(file.filename)
    source_key_seed = object_key("organizations", context.organization.id, "uploads", filename)
    job = Job(
        organization_id=context.organization.id,
        user_id=context.user.id,
        source_filename=filename,
        source_object_key=source_key_seed,
        source_size_bytes=size,
        source_content_type=file.content_type or content_type_for(filename),
        model=model,
        segment=segment,
        overlap=overlap,
        shifts=shifts,
        status="queued",
        stage="Queued",
        progress=0,
    )
    db.add(job)
    db.flush()

    source_key = object_key("organizations", context.organization.id, "jobs", job.id, "source", filename)
    job.source_object_key = source_key
    get_storage_service().put_fileobj(file.file, source_key, job.source_content_type)

    db.add(
        UsageLedger(
            organization_id=context.organization.id,
            user_id=context.user.id,
            job_id=job.id,
            event_type="job_created",
            units=1,
        )
    )
    db.commit()
    db.refresh(job)

    get_event_store().append_event(job.id, "queued", {"filename": filename, "model": model})
    try:
        enqueue_split_job(job.id)
    except Exception as exc:
        job.status = "error"
        job.stage = "Queue error"
        job.error_message = str(exc)
        db.commit()
        get_event_store().append_event(job.id, "queue_error", {"error": str(exc)})
        raise HTTPException(status_code=503, detail="Could not enqueue job") from exc
    return job


def get_owned_job(db: Session, context: AuthContext, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.organization_id != context.organization.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def list_jobs(db: Session, context: AuthContext, limit: int = 50) -> list[Job]:
    safe_limit = max(1, min(limit, 100))
    return (
        db.query(Job)
        .filter(Job.organization_id == context.organization.id)
        .order_by(Job.created_at.desc())
        .limit(safe_limit)
        .all()
    )


def request_cancel(db: Session, context: AuthContext, job_id: str) -> Job:
    job = get_owned_job(db, context, job_id)
    job.cancel_requested = True
    if job.status in {"queued", "running"}:
        job.stage = "Cancellation requested"
    db.commit()
    db.refresh(job)
    get_event_store().append_event(job.id, "cancel_requested", {"user_id": context.user.id})
    return job


def get_artifact(db: Session, context: AuthContext, job_id: str, stem_name: str) -> JobArtifact:
    job = get_owned_job(db, context, job_id)
    artifact = (
        db.query(JobArtifact)
        .filter(JobArtifact.job_id == job.id, JobArtifact.name == stem_name)
        .first()
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Stem not found")
    return artifact


def job_to_dict(job: Job, include_waveform: bool = True) -> dict:
    artifacts = list(job.artifacts or [])
    waveform = get_event_store().get_waveform(job.id) if include_waveform else {}
    return {
        "id": job.id,
        "source_filename": job.source_filename,
        "source_size_bytes": job.source_size_bytes,
        "model": job.model,
        "segment": job.segment,
        "overlap": job.overlap,
        "shifts": job.shifts,
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "cancel_requested": job.cancel_requested,
        "error_message": job.error_message or "",
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "artifacts": artifacts,
        "stems": [{"name": item.name, "path": item.object_key} for item in artifacts],
        "waveform": waveform.get("original", []),
        "stem_waveforms": waveform.get("stems", {}),
    }

