"""Cross-cutting platform tables: raw documents, ingestion runs, embeddings, audit log."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ... import enums as e
from ...reference import EMBEDDING_DIM
from .. import enum_types as t
from ..base import Base, CreatedAtMixin, JSONType, UUIDPrimaryKeyMixin, embedding_type


class Document(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A raw uploaded file. The bytes live in Supabase Storage; only metadata is here."""

    __tablename__ = "documents"

    doc_type: Mapped[e.DocumentType] = mapped_column(t.document_type, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)  # "<bucket>/<object key>"
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    processing_status: Mapped[e.ProcessingStatus] = mapped_column(
        t.processing_status, default=e.ProcessingStatus.PENDING, nullable=False
    )
    pii_redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    redacted_text: Mapped[str | None] = mapped_column(Text)  # OCR/parsing output after PII masking
    extraction: Mapped[dict | None] = mapped_column(JSONType)  # NER output (entities + spans)
    error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestionJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ingestion_jobs"

    source: Mapped[e.IngestionSource] = mapped_column(t.ingestion_source, nullable=False)
    status: Mapped[e.ProcessingStatus] = mapped_column(
        t.processing_status, default=e.ProcessingStatus.PENDING, nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"))
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    records_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_ok: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Embedding(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One vector per (entity, model). Polymorphic on purpose: WP3 indexes several entity kinds."""

    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "model_name", name="embeddings_entity_model_key"),
    )

    entity_type: Mapped[e.EmbeddingEntity] = mapped_column(t.embedding_entity, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(embedding_type(EMBEDDING_DIM), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # re-embed only when the source text changes


class AuditLog(CreatedAtMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    actor_service: Mapped[str | None] = mapped_column(String(32))  # e.g. "wp3-matching"
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "candidate.pii.read"
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
