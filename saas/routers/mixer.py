from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from saas.db.mongo import get_event_store
from saas.db.postgres import get_db
from saas.dependencies import AuthContext, get_current_context
from saas.services.jobs import get_owned_job, job_to_dict
from saas.services.storage import get_storage_service


router = APIRouter(prefix="/api/v1/mixer", tags=["mixer"])

PALETTE = ["#ff4d6d", "#4fc3f7", "#ffd166", "#8be9c1", "#c77dff", "#ff9f1c", "#2ec4b6", "#e76f51"]


@router.get("/{job_id}")
def get_mixer_track_info(
    job_id: str,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = get_owned_job(db, context, job_id)
    if job.status != "done":
        return {
            "ready": False,
            "job_id": job.id,
            "status": job.status,
            "message": "Separation must be complete to use the mixer.",
        }

    job_data = job_to_dict(job, include_waveform=True)
    artifacts = list(job.artifacts or [])

    # Check for saved mixer state from mongo event store
    event_store = get_event_store()
    saved_state = None
    try:
        events = event_store.list_events(job.id, limit=50)
        for ev in reversed(events):
            if ev.get("type") == "mixer_state_saved":
                saved_state = ev.get("payload")
                break
    except Exception:
        pass

    stems = []
    storage = get_storage_service()
    for index, art in enumerate(artifacts):
        stems.append({
            "name": art.name,
            "color": PALETTE[index % len(PALETTE)],
            "size_bytes": art.size_bytes,
            "content_type": art.content_type,
            "waveform": job_data.get("stem_waveforms", {}).get(art.name, []),
            "download_url": f"/api/v1/jobs/{job.id}/download/{art.name}",
        })

    return {
        "ready": True,
        "job_id": job.id,
        "track_name": job.source_filename,
        "model": job.model,
        "stems": stems,
        "original_waveform": job_data.get("waveform", []),
        "saved_state": saved_state,
    }


@router.put("/{job_id}/state")
def update_mixer_state(
    job_id: str,
    state: dict = Body(..., example={"volumes": {"vocals": 0.8}, "muted": {"drums": True}, "solo": "", "master_volume": 0.9}),
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = get_owned_job(db, context, job_id)
    get_event_store().append_event(job.id, "mixer_state_saved", state)
    return {
        "ok": True,
        "job_id": job.id,
        "state": state,
    }


@router.get("/{job_id}/stems")
def list_mixer_stems(
    job_id: str,
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    job = get_owned_job(db, context, job_id)
    artifacts = list(job.artifacts or [])
    return [
        {
            "name": art.name,
            "size_bytes": art.size_bytes,
            "content_type": art.content_type,
            "download_url": f"/api/v1/jobs/{job.id}/download/{art.name}",
        }
        for art in artifacts
    ]
