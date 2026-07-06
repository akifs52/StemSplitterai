import mimetypes
import os
import shutil
from pathlib import Path
from urllib.parse import quote

from saas.core.config import get_settings


class LocalStorageService:
    is_local = True

    def __init__(self) -> None:
        self.root = get_settings().storage_local_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = Path(*[part for part in key.split("/") if part not in {"", ".", ".."}])
        return self.root / safe

    def put_fileobj(self, fileobj, key: str, content_type: str | None = None) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            shutil.copyfileobj(fileobj, fh)

    def put_path(self, path: str | Path, key: str, content_type: str | None = None) -> None:
        dst = self._path(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)

    def download_to_path(self, key: str, path: str | Path) -> None:
        shutil.copy2(self._path(key), path)

    def local_path(self, key: str) -> Path:
        return self._path(key)

    def presigned_get_url(self, key: str, filename: str | None = None) -> str:
        suffix = f"?filename={quote(filename)}" if filename else ""
        return f"/api/v1/storage/local/{quote(key, safe='')}{suffix}"


class S3StorageService:
    is_local = False

    def __init__(self) -> None:
        settings = get_settings()
        import boto3
        from botocore.config import Config

        kwargs = {
            "aws_access_key_id": settings.s3_access_key_id,
            "aws_secret_access_key": settings.s3_secret_access_key,
            "region_name": settings.s3_region,
            "config": Config(s3={"addressing_style": "path"}),
        }
        if settings.s3_endpoint_url:
            kwargs["endpoint_url"] = settings.s3_endpoint_url
        self.client = boto3.client("s3", **kwargs)
        self.bucket = settings.s3_bucket
        self.presign_seconds = settings.storage_presign_seconds

    def put_fileobj(self, fileobj, key: str, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type or "application/octet-stream"}
        self.client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs=extra)

    def put_path(self, path: str | Path, key: str, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"}
        self.client.upload_file(str(path), self.bucket, key, ExtraArgs=extra)

    def download_to_path(self, key: str, path: str | Path) -> None:
        self.client.download_file(self.bucket, key, str(path))

    def presigned_get_url(self, key: str, filename: str | None = None) -> str:
        params = {"Bucket": self.bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=self.presign_seconds,
        )


def get_storage_service():
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3StorageService()
    return LocalStorageService()


def object_key(*parts: str) -> str:
    cleaned = []
    for part in parts:
        value = "/".join(
            segment for segment in str(part).replace("\\", "/").split("/") if segment not in {"", ".", ".."}
        ).strip("/")
        value = "".join(ch if ch.isalnum() or ch in "._-/" else "_" for ch in value)
        cleaned.append(value)
    return "/".join(item for item in cleaned if item)


def content_type_for(path_or_name: str, fallback: str = "application/octet-stream") -> str:
    return mimetypes.guess_type(path_or_name)[0] or fallback


def file_size(fileobj) -> int:
    current = fileobj.tell()
    fileobj.seek(0, os.SEEK_END)
    size = fileobj.tell()
    fileobj.seek(current)
    return size
