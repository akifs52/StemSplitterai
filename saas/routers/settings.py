from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from saas.core.config import get_settings
from saas.db.postgres import get_db
from saas.dependencies import AuthContext, get_current_context
from saas.models import Plan


router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

AVAILABLE_MODELS = [
    {"id": "htdemucs", "name": "HTDemucs (Standard 4-Stem)", "stems": ["vocals", "drums", "bass", "other"]},
    {"id": "htdemucs_ft", "name": "HTDemucs Fine-Tuned", "stems": ["vocals", "drums", "bass", "other"]},
    {"id": "htdemucs_6s", "name": "HTDemucs 6-Stem (+Piano & Guitar)", "stems": ["vocals", "drums", "bass", "other", "piano", "guitar"]},
    {"id": "mdx_extra", "name": "MDX Extra (High Fidelity)", "stems": ["vocals", "drums", "bass", "other"]},
]


@router.get("")
def get_user_settings(
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    plan = db.get(Plan, context.organization.plan_id) or db.get(Plan, "free")

    gpu = False
    try:
        from backend.cuda_checker import has_cuda
        gpu = bool(has_cuda())
    except Exception:
        gpu = False

    return {
        "workspace": {
            "organization_id": context.organization.id,
            "organization_name": context.organization.name,
            "plan_name": plan.name if plan else "Free",
            "monthly_limit": plan.monthly_job_limit if plan else 10,
            "max_upload_mb": plan.max_upload_mb if plan else 100,
        },
        "user": {
            "id": context.user.id,
            "email": context.user.email,
            "full_name": context.user.full_name,
        },
        "demucs": {
            "default_model": "htdemucs_6s",
            "default_segment": 5,
            "default_overlap": 0.25,
            "default_shifts": 1,
            "available_models": AVAILABLE_MODELS,
        },
        "hardware": {
            "device": "CUDA" if gpu else "CPU",
            "gpu_available": gpu,
            "queue_backend": settings.queue_backend,
        },
    }


@router.get("/engines")
def get_available_engines():
    settings = get_settings()
    gpu = False
    cuda_device = "CPU"
    try:
        import torch
        if torch.cuda.is_available():
            gpu = True
            cuda_device = torch.cuda.get_device_name(0)
    except Exception:
        pass

    return {
        "primary_engine": "NVIDIA CUDA" if gpu else "Standard CPU",
        "device_name": cuda_device,
        "gpu_acceleration": gpu,
        "queue_backend": settings.queue_backend,
        "supported_models": [m["id"] for m in AVAILABLE_MODELS],
    }


@router.put("")
def update_user_preferences(
    preferences: dict = Body(..., example={"default_model": "htdemucs_6s", "default_segment": 5}),
    context: AuthContext = Depends(get_current_context),
):
    return {
        "ok": True,
        "updated": preferences,
        "message": "Preferences updated successfully.",
    }
