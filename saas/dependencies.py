from dataclasses import dataclass
from datetime import timezone

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from saas.core.security import decode_access_token, token_hash, utcnow
from saas.db.postgres import get_db
from saas.models import ApiToken, Organization, OrganizationMember, User


bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    organization: Organization
    token: ApiToken | None = None


def get_current_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    stored = (
        db.query(ApiToken)
        .filter(ApiToken.token_hash == token_hash(credentials.credentials), ApiToken.revoked_at.is_(None))
        .first()
    )
    if stored is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not active")
    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not active")

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active")

    membership_query = db.query(OrganizationMember).filter(OrganizationMember.user_id == user.id)
    if organization_id:
        membership_query = membership_query.filter(OrganizationMember.organization_id == organization_id)
    membership = membership_query.order_by(OrganizationMember.created_at.asc()).first()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization access")

    stored.last_used_at = utcnow()
    db.commit()
    organization = db.get(Organization, membership.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization not found")
    return AuthContext(user=user, organization=organization, token=stored)
