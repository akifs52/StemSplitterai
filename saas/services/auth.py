import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from saas.core.security import create_access_token, hash_password, token_hash, verify_password
from saas.models import ApiToken, Organization, OrganizationMember, User
from saas.schemas import AuthResponse
from saas.services.plans import get_free_plan


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "organization"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug = base
    index = 2
    while db.query(Organization).filter(Organization.slug == slug).first() is not None:
        slug = f"{base}-{index}"
        index += 1
    return slug


def issue_auth_response(db: Session, user: User, organization: Organization) -> AuthResponse:
    token, expires_at = create_access_token(user.id)
    db.add(ApiToken(user_id=user.id, token_hash=token_hash(token), expires_at=expires_at))
    db.commit()
    db.refresh(user)
    db.refresh(organization)
    return AuthResponse(access_token=token, user=user, organization=organization)


def register_user(db: Session, email: str, password: str, full_name: str = "", organization_name: str | None = None):
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    plan = get_free_plan(db)
    user = User(email=email, password_hash=hash_password(password), full_name=full_name.strip())
    db.add(user)
    db.flush()

    org_name = (organization_name or f"{full_name or email.split('@')[0]}'s Workspace").strip()
    organization = Organization(
        name=org_name,
        slug=_unique_slug(db, org_name),
        plan_id=plan.id,
        created_by_user_id=user.id,
    )
    db.add(organization)
    db.flush()
    db.add(OrganizationMember(organization_id=organization.id, user_id=user.id, role="owner"))
    db.commit()
    return issue_auth_response(db, user, organization)


def login_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.created_at.asc())
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization access")
    organization = db.get(Organization, membership.organization_id)
    return issue_auth_response(db, user, organization)

