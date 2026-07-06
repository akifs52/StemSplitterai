import os
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("STEM_APP_NAME", "StemSplit AI SaaS")
        self.environment = os.getenv("STEM_ENV", "development")
        self.api_version = os.getenv("STEM_API_VERSION", "v1")

        self.database_url = os.getenv(
            "STEM_DATABASE_URL",
            "postgresql+psycopg://stemsplit:stemsplit@postgres:5432/stemsplit",
        )
        self.mongo_uri = os.getenv("STEM_MONGO_URI", "mongodb://mongo:27017")
        self.mongo_database = os.getenv("STEM_MONGO_DATABASE", "stemsplit")
        self.mongo_backend = os.getenv("STEM_MONGO_BACKEND", "mongo")

        self.redis_url = os.getenv("STEM_REDIS_URL", "redis://redis:6379/0")
        self.queue_backend = os.getenv("STEM_QUEUE_BACKEND", "rq")
        self.rq_queue_name = os.getenv("STEM_RQ_QUEUE", "stemsplit-jobs")

        self.storage_backend = os.getenv("STEM_STORAGE_BACKEND", "local")
        self.storage_local_dir = Path(os.getenv("STEM_STORAGE_LOCAL_DIR", str(BASE_DIR / "storage")))
        self.s3_endpoint_url = os.getenv("STEM_S3_ENDPOINT_URL", "")
        self.s3_bucket = os.getenv("STEM_S3_BUCKET", "stemsplit")
        self.s3_access_key_id = os.getenv("STEM_S3_ACCESS_KEY_ID", "stemsplit")
        self.s3_secret_access_key = os.getenv("STEM_S3_SECRET_ACCESS_KEY", "stemsplit-secret")
        self.s3_region = os.getenv("STEM_S3_REGION", "us-east-1")
        self.storage_presign_seconds = int(os.getenv("STEM_STORAGE_PRESIGN_SECONDS", "3600"))

        self.auth_secret_key = os.getenv("STEM_AUTH_SECRET_KEY", "change-me-in-production")
        self.access_token_expire_minutes = int(os.getenv("STEM_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
        self.public_base_url = os.getenv("STEM_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.oauth_state_expire_minutes = int(os.getenv("STEM_OAUTH_STATE_EXPIRE_MINUTES", "10"))
        self.google_client_id = os.getenv("STEM_GOOGLE_CLIENT_ID", "")
        self.google_client_secret = os.getenv("STEM_GOOGLE_CLIENT_SECRET", "")
        self.apple_client_id = os.getenv("STEM_APPLE_CLIENT_ID", "")
        self.apple_team_id = os.getenv("STEM_APPLE_TEAM_ID", "")
        self.apple_key_id = os.getenv("STEM_APPLE_KEY_ID", "")
        self.apple_private_key = os.getenv("STEM_APPLE_PRIVATE_KEY", "")
        self.apple_private_key_path = os.getenv("STEM_APPLE_PRIVATE_KEY_PATH", "")
        self.legacy_compat_enabled = _env_bool(
            "STEM_LEGACY_COMPAT_ENABLED",
            self.environment != "production",
        )

        self.static_dir = Path(os.getenv("STEM_STATIC_DIR", str(BASE_DIR / "web" / "static")))
        self.assets_dir = Path(os.getenv("STEM_ASSETS_DIR", str(BASE_DIR / "assets")))
        self.upload_temp_dir = Path(os.getenv("STEM_UPLOAD_TEMP_DIR", str(BASE_DIR / "uploads")))
        self.output_temp_dir = Path(os.getenv("STEM_OUTPUT_TEMP_DIR", str(BASE_DIR / "separated" / "web")))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
