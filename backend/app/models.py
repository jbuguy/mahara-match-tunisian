import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class CompanySize(str, enum.Enum):
    SMALL = "1-10"
    MEDIUM = "11-50"
    LARGE = "51-200"
    ENTERPRISE = "200+"


class Employer(Base):
    __tablename__ = "employers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    company_size: Mapped[CompanySize] = mapped_column(Enum(CompanySize, name="company_size"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)