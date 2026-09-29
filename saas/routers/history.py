from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from saas.db.postgres import get_db
from saas.dependencies import AuthContext, get_current_context
from saas.models import Job
from saas.services.jobs import get_owned_job, job_to_dict
from saas.services.queue import enqueue_split_job


router = APIRouter(prefix="/api/v1/history", tags=["history"])


@router.get("")
def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    query = db.query(Job).filter(Job.organization_id == context.organization.id)

    if status:
        query = query.filter(Job.status == status)
    if search:
        query = query.filter(Job.source_filename.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": [job_to_dict(j, include_waveform=False) for j in jobs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
    }


@router.delete("/{job_id}")
def delete_history_item(
    job_id: str,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = get_owned_job(db, context, job_id)
    db.delete(job)
    db.commit()
    return {"ok": True, "deleted_job_id": job_id}


@router.post("/{job_id}/retry")
def retry_job(
    job_id: str,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = get_owned_job(db, context, job_id)
    job.status = "queued"
    job.stage = "Queued for retry"
    job.progress = 0
    job.error_message = ""
    db.commit()
    db.refresh(job)

    try:
        enqueue_split_job(job.id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not enqueue retry") from exc

    return {"ok": True, "job": job_to_dict(job, include_waveform=False)}
