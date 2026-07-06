from fastapi import APIRouter

from saas.core.config import get_settings


router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/system")
def system_info():
    settings = get_settings()
    gpu = False
    try:
        from backend.cuda_checker import has_cuda

        gpu = bool(has_cuda())
    except Exception:
        gpu = False

    queue_ready = True
    if settings.queue_backend == "rq":
        try:
            from redis import Redis

            Redis.from_url(settings.redis_url).ping()
        except Exception:
            queue_ready = False

    return {
        "gpu": gpu,
        "device": "CUDA" if gpu else "CPU",
        "queue_backend": settings.queue_backend,
        "queue_ready": queue_ready,
        "api_version": settings.api_version,
    }

