import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Numeric, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from mahara_data.db.base import JSONType, pg_enum
from mahara_data.enums import EducationLevel, LiteracyLevel, OnboardingPath, UserRole

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

    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"), default=UserRole.CANDIDATE, nullable=False
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(8), default="ar-TN", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roles: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
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
        Enum(
            AuthProvider,
            name="auth_identity_provider",
            values_callable=lambda enum: [member.value for member in enum],
            native_enum=False,
        ),
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
    __table_args__ = (CheckConstraint("years_experience >= 0", name="candidates_years_experience_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    onboarding_path: Mapped[OnboardingPath] = mapped_column(
        pg_enum(OnboardingPath, "onboarding_path"), default=OnboardingPath.CV_UPLOAD, nullable=False
    )
    literacy_level: Mapped[LiteracyLevel] = mapped_column(
        pg_enum(LiteracyLevel, "literacy_level"), default=LiteracyLevel.LITERATE, nullable=False
    )
    governorate_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    education_level: Mapped[EducationLevel | None] = mapped_column(pg_enum(EducationLevel, "education_level"))
    years_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    languages: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship()

    @property
    def preferred_language(self) -> str:
        return self.user.preferred_language

    @preferred_language.setter
    def preferred_language(self, value: str) -> None:
        self.user.preferred_language = value
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
        user = User(
            email=normalized_email,
            role=UserRole(roles[0]) if roles else UserRole.CANDIDATE,
            email_verified=bool(email_verified),
            roles=[],
        )
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
    if user.role is UserRole.CANDIDATE and normalized_role != UserRole.CANDIDATE.value:
        user.role = UserRole(normalized_role)


def get_or_create_candidate_for_user(db, user: User, *, onboarding_path: str = "cv_upload") -> Candidate:
    ensure_user_has_role(user, "candidate")
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if candidate is None:
        candidate = Candidate(
            user_id=user.id,
            onboarding_path=OnboardingPath(onboarding_path),
            literacy_level=LiteracyLevel.LITERATE,
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
    state: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    messages: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    draft: Mapped[dict | None] = mapped_column(JSONType)
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
    answers: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )