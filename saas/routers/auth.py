from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from saas.core.security import decode_oauth_state, utcnow
from saas.db.postgres import get_db
from saas.dependencies import AuthContext, get_current_context
from saas.schemas import AuthResponse, LoginRequest, RegisterRequest
from saas.services.auth import login_user, register_user
from saas.services.oauth import authorization_url, exchange_code, profile_from_id_token, provider_status, upsert_oauth_user


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        organization_name=payload.organization_name,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return login_user(db, email=payload.email, password=payload.password)


@router.post("/logout")
def logout(context: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    if context.token is not None:
        context.token.revoked_at = utcnow()
        db.commit()
    return {"ok": True}


@router.get("/providers")
def providers():
    return provider_status()


@router.get("/oauth/{provider}/start")
def oauth_start(provider: str, mode: str = Query(default="login")):
    return RedirectResponse(authorization_url(provider, mode=mode))


def _oauth_success_redirect(token: str) -> RedirectResponse:
    return RedirectResponse(f"/auth/callback#access_token={quote(token)}")


def _oauth_error_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(f"/auth/callback#oauth_error={quote(message)}")


async def _handle_oauth_callback(
    provider: str,
    code: str | None,
    state: str | None,
    error: str | None,
    user_payload: str | None,
    db: Session,
):
    if error:
        return _oauth_error_redirect(error)
    if not code or not state:
        return _oauth_error_redirect("Missing OAuth callback data")
    try:
        decode_oauth_state(state, provider)
        token_payload = await exchange_code(provider, code)
        id_token = token_payload.get("id_token")
        if not id_token:
            raise HTTPException(status_code=401, detail="OAuth provider did not return an identity token")
        profile = profile_from_id_token(provider, id_token, user_payload=user_payload)
        auth_response = upsert_oauth_user(db, profile)
        return _oauth_success_redirect(auth_response.access_token)
    except HTTPException as exc:
        return _oauth_error_redirect(str(exc.detail))
    except Exception:
        return _oauth_error_redirect("OAuth sign-in failed")


@router.get("/oauth/{provider}/callback")
async def oauth_callback_get(
    provider: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return await _handle_oauth_callback(provider, code, state, error, None, db)


@router.post("/oauth/{provider}/callback")
async def oauth_callback_post(
    provider: str,
    code: str | None = Form(default=None),
    state: str | None = Form(default=None),
    error: str | None = Form(default=None),
    user: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    return await _handle_oauth_callback(provider, code, state, error, user, db)
