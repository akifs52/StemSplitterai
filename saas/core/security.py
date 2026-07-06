import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from saas.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_b64, digest_b64 = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _b64_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _sign(payload_part: str) -> str:
    secret = get_settings().auth_secret_key.encode("utf-8")
    return _b64_encode(hmac.new(secret, payload_part.encode("ascii"), hashlib.sha256).digest())


def create_access_token(user_id: str, minutes: int | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = utcnow() + timedelta(minutes=minutes or settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "typ": "access",
        "jti": secrets.token_urlsafe(16),
        "exp": int(expires_at.timestamp()),
    }
    payload_part = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_part}.{_sign(payload_part)}", expires_at


def create_oauth_state(provider: str, mode: str = "login", minutes: int | None = None) -> str:
    settings = get_settings()
    expires_at = utcnow() + timedelta(minutes=minutes or settings.oauth_state_expire_minutes)
    payload = {
        "provider": provider,
        "mode": mode,
        "typ": "oauth_state",
        "jti": secrets.token_urlsafe(16),
        "exp": int(expires_at.timestamp()),
    }
    payload_part = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_part}.{_sign(payload_part)}"


def decode_access_token(token: str) -> dict:
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid token") from exc
    if not hmac.compare_digest(_sign(payload_part), signature):
        raise ValueError("Invalid token signature")
    payload = json.loads(_b64_decode(payload_part))
    if payload.get("typ") != "access":
        raise ValueError("Invalid token type")
    if int(payload.get("exp", 0)) < int(utcnow().timestamp()):
        raise ValueError("Token expired")
    return payload


def decode_oauth_state(token: str, provider: str) -> dict:
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid OAuth state") from exc
    if not hmac.compare_digest(_sign(payload_part), signature):
        raise ValueError("Invalid OAuth state signature")
    payload = json.loads(_b64_decode(payload_part))
    if payload.get("typ") != "oauth_state":
        raise ValueError("Invalid OAuth state type")
    if payload.get("provider") != provider:
        raise ValueError("OAuth provider mismatch")
    if int(payload.get("exp", 0)) < int(utcnow().timestamp()):
        raise ValueError("OAuth state expired")
    return payload
