from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from saas.db.mongo import get_event_store
from saas.db.postgres import get_db
from saas.dependencies import AuthContext, get_current_context
from saas.schemas import CreateJobResponse, JobRead
from saas.services.jobs import create_job, get_artifact, get_owned_job, job_to_dict, list_jobs, request_cancel
from saas.services.storage import get_storage_service


router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("", response_model=CreateJobResponse)
async def create_job_endpoint(
    file: UploadFile = File(...),
    model: str = Form("htdemucs_6s"),
    segment: int = Form(5),
    overlap: float = Form(0.25),
    shifts: int = Form(1),
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = create_job(db, context, file, model=model, segment=segment, overlap=overlap, shifts=shifts)
    return CreateJobResponse(job_id=job.id)


@router.get("", response_model=list[JobRead])
def list_jobs_endpoint(
    limit: int = 50,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    return [job_to_dict(job, include_waveform=False) for job in list_jobs(db, context, limit=limit)]


@router.get("/{job_id}", response_model=JobRead)
def get_job_endpoint(
    job_id: str,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    return job_to_dict(get_owned_job(db, context, job_id))


@router.post("/{job_id}/cancel", response_model=JobRead)
def cancel_job_endpoint(
    job_id: str,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    return job_to_dict(request_cancel(db, context, job_id))


@router.get("/{job_id}/download/{stem_name}")
def download_stem_endpoint(
    job_id: str,
    stem_name: str,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    artifact = get_artifact(db, context, job_id, stem_name)
    storage = get_storage_service()
    if storage.is_local:
        return FileResponse(storage.local_path(artifact.object_key), media_type=artifact.content_type, filename=artifact.name)
    return RedirectResponse(storage.presigned_get_url(artifact.object_key, artifact.name))


@router.get("/{job_id}/events")
def job_events_endpoint(
    job_id: str,
    limit: int = 200,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    get_owned_job(db, context, job_id)
    return get_event_store().list_events(job_id, limit=limit)

