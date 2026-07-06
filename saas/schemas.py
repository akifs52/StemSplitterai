from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    monthly_job_limit: int
    max_upload_mb: int


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    created_at: datetime


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    plan: PlanRead | None = None


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str = ""
    organization_name: str | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Invalid email")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    organization: OrganizationRead


class MeResponse(BaseModel):
    user: UserRead
    organization: OrganizationRead


class JobArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_filename: str
    source_size_bytes: int
    model: str
    segment: int
    overlap: float
    shifts: int
    status: str
    stage: str
    progress: int
    cancel_requested: bool
    error_message: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    artifacts: list[JobArtifactRead] = Field(default_factory=list)
    stems: list[dict] = Field(default_factory=list)
    waveform: list = Field(default_factory=list)
    stem_waveforms: dict = Field(default_factory=dict)


class CreateJobResponse(BaseModel):
    job_id: str


class JobEventRead(BaseModel):
    job_id: str
    type: str | None = None
    payload: dict = Field(default_factory=dict)
    line: str | None = None
    created_at: str


class SystemRead(BaseModel):
    gpu: bool
    device: str
    queue_backend: str
    queue_ready: bool
    api_version: str
