import os
import shutil
import tempfile

DB_DIR = tempfile.mkdtemp(prefix="stemsplit-test-db-")
STORAGE_DIR = tempfile.mkdtemp(prefix="stemsplit-test-storage-")

os.environ["STEM_DATABASE_URL"] = f"sqlite:///{DB_DIR}/test.db"
os.environ["STEM_MONGO_BACKEND"] = "memory"
os.environ["STEM_STORAGE_BACKEND"] = "local"
os.environ["STEM_STORAGE_LOCAL_DIR"] = STORAGE_DIR
os.environ["STEM_QUEUE_BACKEND"] = "none"
os.environ["STEM_AUTH_SECRET_KEY"] = "test-secret"
os.environ["STEM_LEGACY_COMPAT_ENABLED"] = "false"

from fastapi.testclient import TestClient

from saas.db.postgres import Base, engine
from saas.main import app
from saas.models import OAuthAccount, Plan, User
from saas.db.postgres import SessionLocal
from saas.services.oauth import OAuthProfile, upsert_oauth_user
from saas.services.storage import object_key


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    shutil.rmtree(STORAGE_DIR, ignore_errors=True)
    shutil.rmtree(DB_DIR, ignore_errors=True)


def _client():
    with TestClient(app) as client:
        yield client


def _register(client: TestClient, email: str = "user@example.com") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "very-secret-password",
            "full_name": "Test User",
            "organization_name": "Test Org",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me_logout():
    for client in _client():
        token = _register(client)
        me = client.get("/api/v1/me", headers=_headers(token))
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "user@example.com"

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "very-secret-password"},
        )
        assert login.status_code == 200

        logout = client.post("/api/v1/auth/logout", headers=_headers(token))
        assert logout.status_code == 200
        assert client.get("/api/v1/me", headers=_headers(token)).status_code == 401


def test_jobs_require_auth():
    for client in _client():
        response = client.get("/api/v1/jobs")
        assert response.status_code == 401


def test_create_job_quota_and_events():
    for client in _client():
        token = _register(client)
        response = client.post(
            "/api/v1/jobs",
            headers=_headers(token),
            data={"model": "htdemucs_6s", "segment": "5", "overlap": "0.25", "shifts": "1"},
            files={"file": ("song.wav", b"fake audio bytes", "audio/wav")},
        )
        assert response.status_code == 200, response.text
        job_id = response.json()["job_id"]

        job = client.get(f"/api/v1/jobs/{job_id}", headers=_headers(token))
        assert job.status_code == 200
        assert job.json()["status"] == "queued"
        assert job.json()["source_filename"] == "song.wav"

        events = client.get(f"/api/v1/jobs/{job_id}/events", headers=_headers(token))
        assert events.status_code == 200
        assert any(item.get("type") == "queued" for item in events.json())


def test_upload_size_quota_is_enforced():
    for client in _client():
        db = SessionLocal()
        plan = db.get(Plan, "free")
        plan.max_upload_mb = 0
        db.commit()
        db.close()
        token = _register(client, "quota@example.com")
        response = client.post(
            "/api/v1/jobs",
            headers=_headers(token),
            files={"file": ("large.wav", b"x", "audio/wav")},
        )
        assert response.status_code == 413


def test_tenant_isolation_and_cancel_flag():
    for client in _client():
        token_a = _register(client, "a@example.com")
        token_b = _register(client, "b@example.com")

        created = client.post(
            "/api/v1/jobs",
            headers=_headers(token_a),
            files={"file": ("song.wav", b"fake audio bytes", "audio/wav")},
        )
        assert created.status_code == 200
        job_id = created.json()["job_id"]

        assert client.get(f"/api/v1/jobs/{job_id}", headers=_headers(token_b)).status_code == 404
        cancelled = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=_headers(token_a))
        assert cancelled.status_code == 200
        body = cancelled.json()
        assert body["cancel_requested"] is True
        assert body["stage"] == "Cancellation requested"


def test_storage_key_sanitizes_path_parts():
    assert object_key("organizations", "../bad", "jobs", "x y.wav") == "organizations/bad/jobs/x_y.wav"


def test_oauth_providers_are_disabled_without_credentials():
    for client in _client():
        response = client.get("/api/v1/auth/providers")
        assert response.status_code == 200
        assert response.json() == {"google": False, "apple": False}
        start = client.get("/api/v1/auth/oauth/google/start", follow_redirects=False)
        assert start.status_code == 400


def test_oauth_profile_creates_user_and_links_account():
    db = SessionLocal()
    try:
        auth = upsert_oauth_user(
            db,
            OAuthProfile(
                provider="google",
                subject="google-subject-1",
                email="oauth@example.com",
                email_verified=True,
                name="OAuth User",
            ),
        )
        assert auth.user.email == "oauth@example.com"
        assert auth.organization.name == "OAuth User's Workspace"
        user = db.query(User).filter(User.email == "oauth@example.com").one()
        account = db.query(OAuthAccount).filter(OAuthAccount.user_id == user.id).one()
        assert account.provider == "google"
        assert account.provider_subject == "google-subject-1"
    finally:
        db.close()
