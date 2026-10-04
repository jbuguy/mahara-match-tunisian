import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AuthProvider(str, enum.Enum):
    GOOGLE = "google"
    PASSWORD = "password"


class CompanySize(str, enum.Enum):
    SMALL = "1-10"
    MEDIUM = "11-50"
    LARGE = "51-200"
    ENTERPRISE = "200+"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_auth_identity_user_provider"),
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_identity_provider_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider", values_callable=lambda enum: [member.value for member in enum]),
        nullable=False,
    )
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @classmethod
    def link_user(
        cls,
        db,
        user: User,
        *,
        provider: AuthProvider,
        provider_user_id: str,
        email: str | None = None,
        email_verified: bool = False,
        password_hash: str | None = None,
    ) -> "AuthIdentity":
        normalized_email = normalize_email(email or user.email)
        linked_identity = (
            db.query(cls)
            .filter(cls.provider == provider, cls.provider_user_id == str(provider_user_id))
            .first()
        )
        if linked_identity and linked_identity.user_id != user.id:
            raise ValueError("This authentication identity is already linked to another user")

        existing = db.query(cls).filter(cls.user_id == user.id, cls.provider == provider).first()
        if existing is not None:
            existing.provider_user_id = str(provider_user_id)
            existing.email = normalized_email
            existing.email_verified = bool(email_verified or existing.email_verified)
            if password_hash is not None:
                existing.password_hash = password_hash
            db.flush()
            return existing

        identity = cls(
            user_id=user.id,
            provider=provider,
            provider_user_id=str(provider_user_id),
            email=normalized_email,
            email_verified=bool(email_verified),
            password_hash=password_hash,
        )
        db.add(identity)
        db.flush()
        return identity


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    onboarding_path: Mapped[str] = mapped_column(String(80), default="cv_upload", nullable=False)
    literacy_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    governorate_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    years_experience: Mapped[int | None] = mapped_column(nullable=True)
    languages: Mapped[list[dict] | list] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    available_from: Mapped[str | None] = mapped_column(String(30), nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Employer(Base):
    __tablename__ = "employers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    company_size: Mapped[CompanySize] = mapped_column(
        Enum(CompanySize, name="company_size", values_callable=lambda enum: [member.value for member in enum]),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


def get_or_create_user(db, email: str, *, roles: list[str] | None = None, email_verified: bool = False) -> User:
    normalized_email = normalize_email(email)
    user = db.query(User).filter(User.email == normalized_email).first()
    if user is None:
        user = User(email=normalized_email, email_verified=bool(email_verified), roles=[])
        db.add(user)
        db.flush()

    if email_verified:
        user.email_verified = True

    for role in roles or []:
        ensure_user_has_role(user, role)

    db.flush()
    return user


def ensure_user_has_role(user: User, role: str) -> None:
    normalized_role = (role or "").strip().lower()
    if not normalized_role:
        return
    if normalized_role not in user.roles:
        user.roles = [*user.roles, normalized_role]


def get_or_create_candidate_for_user(db, user: User, *, onboarding_path: str = "cv_upload") -> Candidate:
    ensure_user_has_role(user, "candidate")
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if candidate is None:
        candidate = Candidate(
            user_id=user.id,
            onboarding_path=onboarding_path,
            preferred_language="fr",
        )
        db.add(candidate)
        db.flush()
    else:
        candidate.onboarding_path = onboarding_path or candidate.onboarding_path
    return candidate


class EmployerDraftSession(Base):
    __tablename__ = "employer_draft_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("employers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    messages: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    draft: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

class CandidateOnboardingSession(Base):
    __tablename__ = "candidate_onboarding_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )