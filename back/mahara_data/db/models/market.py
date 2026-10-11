"""Labour-market data injected by the Ministry (WP5), official or informal."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from .. import enum_types as t
from ..base import Base, CreatedAtMixin, JSONType, UUIDPrimaryKeyMixin


class MarketDataset(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "market_datasets"
    __table_args__ = (CheckConstraint("period_start <= period_end", name="market_datasets_period_order"),)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    origin: Mapped[e.MarketDataOrigin] = mapped_column(t.market_data_origin, nullable=False)
    publisher: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g. "Ministère de l'Emploi", "INS"
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"))
    ingestion_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("ingestion_jobs.id"))
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))


class MarketIndicator(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "market_indicators"
    __table_args__ = (
        Index("market_indicators_lookup_idx", "indicator_type", "governorate_code", "period_start"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("market_datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    indicator_type: Mapped[e.MarketIndicatorType] = mapped_column(t.market_indicator_type, nullable=False)
    occupation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("occupations.id"))
    skill_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id"))
    sector_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sectors.id"))
    governorate_code: Mapped[str | None] = mapped_column(String(8), ForeignKey("governorates.code"))
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)  # count | percent | tnd
    extra: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
