from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from saas.core.config import get_settings
from saas.db.postgres import get_db
from saas.dependencies import AuthContext, get_current_context
from saas.models import Job
from saas.services.jobs import create_job, get_owned_job, job_to_dict, list_jobs


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def format_bytes(bytes_num: int) -> str:
    if not bytes_num:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    idx = 0
    size = float(bytes_num)
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    return f"{size:.1f} {units[idx]}"


@router.get("/overview")
def get_dashboard_overview(
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    org_id = context.organization.id

    # Aggregated Stats
    total_jobs = db.query(Job).filter(Job.organization_id == org_id).count()
    completed_jobs = db.query(Job).filter(Job.organization_id == org_id, Job.status == "done").count()
    running_jobs = db.query(Job).filter(Job.organization_id == org_id, Job.status.in_(["queued", "running"])).count()
    failed_jobs = db.query(Job).filter(Job.organization_id == org_id, Job.status == "error").count()

    total_storage_bytes = (
        db.query(func.coalesce(func.sum(Job.source_size_bytes), 0))
        .filter(Job.organization_id == org_id)
        .scalar()
    )

    # Active or latest job
    active_job = (
        db.query(Job)
        .filter(Job.organization_id == org_id, Job.status.in_(["queued", "running"]))
        .order_by(Job.created_at.desc())
        .first()
    )
    if not active_job:
        active_job = (
            db.query(Job)
            .filter(Job.organization_id == org_id)
            .order_by(Job.created_at.desc())
            .first()
        )

    # Recent jobs (up to 5)
    recent = list_jobs(db, context, limit=5)

    # System Status
    settings = get_settings()
    gpu = False
    try:
        from backend.cuda_checker import has_cuda
        gpu = bool(has_cuda())
    except Exception:
        gpu = False

    return {
        "stats": {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "running_jobs": running_jobs,
            "failed_jobs": failed_jobs,
            "storage_used_bytes": int(total_storage_bytes or 0),
            "storage_formatted": format_bytes(int(total_storage_bytes or 0)),
        },
        "active_job": job_to_dict(active_job, include_waveform=True) if active_job else None,
        "recent_jobs": [job_to_dict(j, include_waveform=False) for j in recent],
        "system": {
            "device": "CUDA" if gpu else "CPU",
            "gpu": gpu,
            "queue_backend": settings.queue_backend,
        },
    }


@router.post("/upload")
async def dashboard_quick_upload(
    file: UploadFile = File(...),
    model: str = Form("htdemucs_6s"),
    segment: int = Form(5),
    overlap: float = Form(0.25),
    shifts: int = Form(1),
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = create_job(db, context, file, model=model, segment=segment, overlap=overlap, shifts=shifts)
    return {
        "job_id": job.id,
        "filename": job.source_filename,
        "status": job.status,
        "model": job.model,
    }
