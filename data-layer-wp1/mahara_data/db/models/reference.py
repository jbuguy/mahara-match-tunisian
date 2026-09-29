import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, UUIDPrimaryKeyMixin


class Governorate(Base):
    """The 24 governorates, seeded by the migration (see mahara_data.reference)."""

    __tablename__ = "governorates"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)  # ISO 3166-2:TN, e.g. "TN-11"
    name_fr: Mapped[str] = mapped_column(String(80), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(80), nullable=False)


class Sector(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sectors"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_fr: Mapped[str] = mapped_column(String(160), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(160))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sectors.id"))
