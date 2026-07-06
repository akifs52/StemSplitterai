from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from saas.services.storage import get_storage_service


router = APIRouter(prefix="/api/v1/storage", tags=["storage"])


@router.get("/local/{encoded_key}")
def local_file(encoded_key: str, filename: str | None = Query(default=None)):
    storage = get_storage_service()
    if not storage.is_local:
        raise HTTPException(status_code=404, detail="Local storage is not enabled")
    key = unquote(encoded_key)
    path = storage.local_path(key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename or path.name)

