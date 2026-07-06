import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from saas.core.config import get_settings
from saas.core.security import create_oauth_state, hash_password, utcnow
from saas.models import OAuthAccount, Organization, OrganizationMember, User
from saas.services.auth import _unique_slug, issue_auth_response
from saas.services.plans import get_free_plan


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


@dataclass
class OAuthProfile:
    provider: str
    subject: str
    email: str
    email_verified: bool
    name: str


def redirect_uri(provider: str) -> str:
    return f"{get_settings().public_base_url}/api/v1/auth/oauth/{provider}/callback"


def provider_status() -> dict:
    settings = get_settings()
    apple_key_ready = bool(settings.apple_private_key or settings.apple_private_key_path)
    return {
        "google": bool(settings.google_client_id and settings.google_client_secret),
        "apple": bool(
            settings.apple_client_id
            and settings.apple_team_id
            and settings.apple_key_id
            and apple_key_ready
        ),
    }


def assert_provider_enabled(provider: str) -> None:
    if provider not in {"google", "apple"}:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    if not provider_status().get(provider):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{provider} OAuth is not configured")


def authorization_url(provider: str, mode: str = "login") -> str:
    assert_provider_enabled(provider)
    settings = get_settings()
    state = create_oauth_state(provider, mode)
    if provider == "google":
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri("google"),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    params = {
        "client_id": settings.apple_client_id,
        "redirect_uri": redirect_uri("apple"),
        "response_type": "code",
        "response_mode": "form_post",
        "scope": "name email",
        "state": state,
    }
    return f"{APPLE_AUTH_URL}?{urlencode(params)}"


def _apple_private_key() -> str:
    settings = get_settings()
    if settings.apple_private_key:
        return settings.apple_private_key.replace("\\n", "\n")
    if settings.apple_private_key_path:
        return Path(settings.apple_private_key_path).read_text(encoding="utf-8")
    raise HTTPException(status_code=500, detail="Apple private key is not configured")


def _apple_client_secret() -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "iss": settings.apple_team_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=20)).timestamp()),
        "aud": "https://appleid.apple.com",
        "sub": settings.apple_client_id,
    }
    return jwt.encode(
        payload,
        _apple_private_key(),
        algorithm="ES256",
        headers={"kid": settings.apple_key_id},
    )


async def exchange_code(provider: str, code: str) -> dict:
    settings = get_settings()
    assert_provider_enabled(provider)
    if provider == "google":
        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("google"),
        }
        token_url = GOOGLE_TOKEN_URL
    else:
        data = {
            "client_id": settings.apple_client_id,
            "client_secret": _apple_client_secret(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("apple"),
        }
        token_url = APPLE_TOKEN_URL

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(token_url, data=data)
    if response.status_code >= 400:
        raise HTTPException(status_code=401, detail=f"{provider} token exchange failed")
    return response.json()


def _decode_id_token(provider: str, id_token: str) -> dict:
    settings = get_settings()
    if provider == "google":
        client_id = settings.google_client_id
        jwks_url = GOOGLE_JWKS_URL
        issuers = ("https://accounts.google.com", "accounts.google.com")
    else:
        client_id = settings.apple_client_id
        jwks_url = APPLE_JWKS_URL
        issuers = ("https://appleid.apple.com",)

    signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(id_token)
    last_error: Exception | None = None
    for issuer in issuers:
        try:
            return jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=client_id,
                issuer=issuer,
            )
        except Exception as exc:
            last_error = exc
    raise HTTPException(status_code=401, detail=f"Invalid {provider} identity token") from last_error


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def profile_from_id_token(provider: str, id_token: str, user_payload: str | None = None) -> OAuthProfile:
    payload = _decode_id_token(provider, id_token)
    email = str(payload.get("email") or "").strip().lower()
    name = str(payload.get("name") or "").strip()
    if provider == "apple" and user_payload:
        try:
            user_info = json.loads(user_payload)
            apple_name = user_info.get("name") or {}
            name = " ".join(
                part
                for part in [apple_name.get("firstName", ""), apple_name.get("lastName", "")]
                if part
            ).strip() or name
        except json.JSONDecodeError:
            pass
    return OAuthProfile(
        provider=provider,
        subject=str(payload.get("sub") or ""),
        email=email,
        email_verified=_truthy(payload.get("email_verified", False)),
        name=name,
    )


def _default_name(profile: OAuthProfile) -> str:
    if profile.name:
        return profile.name
    if profile.email:
        return profile.email.split("@")[0]
    return f"{profile.provider.capitalize()} User"


def upsert_oauth_user(db: Session, profile: OAuthProfile):
    if not profile.subject:
        raise HTTPException(status_code=401, detail="OAuth profile is missing subject")
    if not profile.email:
        raise HTTPException(status_code=401, detail="OAuth provider did not return an email address")
    if not profile.email_verified:
        raise HTTPException(status_code=401, detail="OAuth provider email is not verified")

    account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == profile.provider,
            OAuthAccount.provider_subject == profile.subject,
        )
        .first()
    )
    if account is not None:
        account.email = profile.email
        user = db.get(User, account.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="OAuth account is not linked to an active user")
        if profile.name and not user.full_name:
            user.full_name = profile.name
        db.commit()
        membership = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == user.id)
            .order_by(OrganizationMember.created_at.asc())
            .first()
        )
        if membership is None:
            raise HTTPException(status_code=403, detail="No organization access")
        return issue_auth_response(db, user, db.get(Organization, membership.organization_id))

    user = db.query(User).filter(User.email == profile.email).first()
    if user is None:
        name = _default_name(profile)
        plan = get_free_plan(db)
        user = User(
            email=profile.email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            full_name=name,
        )
        db.add(user)
        db.flush()
        org_name = f"{name}'s Workspace"
        organization = Organization(
            name=org_name,
            slug=_unique_slug(db, org_name),
            plan_id=plan.id,
            created_by_user_id=user.id,
        )
        db.add(organization)
        db.flush()
        db.add(OrganizationMember(organization_id=organization.id, user_id=user.id, role="owner"))
    else:
        membership = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == user.id)
            .order_by(OrganizationMember.created_at.asc())
            .first()
        )
        if membership is None:
            raise HTTPException(status_code=403, detail="No organization access")
        organization = db.get(Organization, membership.organization_id)

    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=profile.provider,
            provider_subject=profile.subject,
            email=profile.email,
        )
    )
    db.commit()
    return issue_auth_response(db, user, organization)

