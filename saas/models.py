import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from saas.core.security import utcnow
from saas.db.postgres import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String(64), primary_key=True)
    name = Column(String(120), nullable=False)
    monthly_job_limit = Column(Integer, nullable=False)
    max_upload_mb = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=uuid_str)
    email = Column(String(320), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(160), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String(160), nullable=False)
    slug = Column(String(180), nullable=False, unique=True, index=True)
    plan_id = Column(String(64), ForeignKey("plans.id"), nullable=False, default="free")
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    plan = relationship("Plan")
    memberships = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)

    id = Column(String(36), primary_key=True, default=uuid_str)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(40), nullable=False, default="member")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    source_filename = Column(String(512), nullable=False)
    source_object_key = Column(String(1024), nullable=False)
    source_size_bytes = Column(Integer, nullable=False, default=0)
    source_content_type = Column(String(160), nullable=False, default="application/octet-stream")
    model = Column(String(80), nullable=False)
    segment = Column(Integer, nullable=False, default=5)
    overlap = Column(Float, nullable=False, default=0.25)
    shifts = Column(Integer, nullable=False, default=1)
    status = Column(String(40), nullable=False, index=True, default="queued")
    stage = Column(String(512), nullable=False, default="Queued")
    progress = Column(Integer, nullable=False, default=0)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    organization = relationship("Organization", back_populates="jobs")
    artifacts = relationship("JobArtifact", back_populates="job", cascade="all, delete-orphan")


class JobArtifact(Base):
    __tablename__ = "job_artifacts"
    __table_args__ = (UniqueConstraint("job_id", "name", name="uq_job_artifact_name"),)

    id = Column(String(36), primary_key=True, default=uuid_str)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    name = Column(String(180), nullable=False)
    object_key = Column(String(1024), nullable=False)
    content_type = Column(String(160), nullable=False, default="audio/wav")
    size_bytes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    job = relationship("Job", back_populates="artifacts")


class UsageLedger(Base):
    __tablename__ = "usage_ledger"

    id = Column(String(36), primary_key=True, default=uuid_str)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=True, index=True)
    event_type = Column(String(80), nullable=False)
    units = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="tokens")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_oauth_provider_subject"),)

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(40), nullable=False, index=True)
    provider_subject = Column(String(255), nullable=False)
    email = Column(String(320), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="oauth_accounts")
