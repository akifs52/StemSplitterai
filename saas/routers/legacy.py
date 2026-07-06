from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from saas.core.config import get_settings
from saas.core.security import hash_password
from saas.db.postgres import get_db
from saas.dependencies import AuthContext
from saas.models import Organization, OrganizationMember, User
from saas.services.jobs import create_job, get_artifact, get_owned_job, job_to_dict, request_cancel
from saas.services.plans import get_free_plan
from saas.services.storage import get_storage_service


router = APIRouter(tags=["legacy"])


def _legacy_context(db: Session) -> AuthContext:
    if not get_settings().legacy_compat_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = db.query(User).filter(User.email == "legacy@local.dev").first()
    if user is None:
        user = User(email="legacy@local.dev", password_hash=hash_password("legacy-local-password"), full_name="Local Demo")
        db.add(user)
        db.flush()
    member = db.query(OrganizationMember).filter(OrganizationMember.user_id == user.id).first()
    if member is None:
        plan = get_free_plan(db)
        organization = Organization(
            name="Local Demo",
            slug="local-demo",
            plan_id=plan.id,
            created_by_user_id=user.id,
        )
        db.add(organization)
        db.flush()
        member = OrganizationMember(organization_id=organization.id, user_id=user.id, role="owner")
        db.add(member)
        db.commit()
    organization = db.get(Organization, member.organization_id)
    return AuthContext(user=user, organization=organization, token=None)


@router.post("/api/jobs")
async def legacy_create_job(
    file: UploadFile = File(...),
    model: str = Form("htdemucs_6s"),
    segment: int = Form(5),
    overlap: float = Form(0.25),
    shifts: int = Form(1),
    db: Session = Depends(get_db),
):
    context = _legacy_context(db)
    job = create_job(db, context, file, model=model, segment=segment, overlap=overlap, shifts=shifts)
    return {"job_id": job.id}


@router.get("/api/jobs/{job_id}")
def legacy_get_job(job_id: str, db: Session = Depends(get_db)):
    context = _legacy_context(db)
    return job_to_dict(get_owned_job(db, context, job_id))


@router.post("/api/jobs/{job_id}/cancel")
def legacy_cancel_job(job_id: str, db: Session = Depends(get_db)):
    context = _legacy_context(db)
    request_cancel(db, context, job_id)
    return {"ok": True}


@router.get("/api/jobs/{job_id}/download/{stem_name}")
def legacy_download_stem(job_id: str, stem_name: str, db: Session = Depends(get_db)):
    context = _legacy_context(db)
    artifact = get_artifact(db, context, job_id, stem_name)
    storage = get_storage_service()
    if storage.is_local:
        return FileResponse(storage.local_path(artifact.object_key), media_type=artifact.content_type, filename=artifact.name)
    return RedirectResponse(storage.presigned_get_url(artifact.object_key, artifact.name))


@router.get("/api/system")
def legacy_system():
    from saas.routers.system import system_info

    return system_info()

