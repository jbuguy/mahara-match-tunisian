"""Candidate data export, de-identification, and scheduled purge."""

import json
import logging
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, BinaryIO

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.models import AccountActionToken, CandidateOnboardingSession
from mahara_data.db.models.accounts import AuthIdentity, User
from mahara_data.db.models.candidates import (
    Candidate,
    CandidateDesiredOccupation,
    CandidateEducation,
    CandidateExperience,
    CandidatePII,
    CandidateSkill,
    ConversationSession,
    MockInterviewSession,
)
from mahara_data.db.models.employers import Application, JobOffer
from mahara_data.db.models.matching import MatchResult, Roadmap, RoadmapItem, SkillGap
from mahara_data.db.models.platform import (
    AnalyticsEvent,
    AuditLog,
    Document,
    IngestionJob,
    NotificationOutbox,
)
from mahara_data.db.models.training import CandidateCertification

from ...config import get_settings

logger = logging.getLogger(__name__)
DELETION_RETENTION_DAYS = 30
EXPORT_SPILL_BYTES = 1024 * 1024
EXPORT_CHUNK_BYTES = 64 * 1024


def _json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, (Decimal,)):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__} in candidate export")


def _row_dict(row: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    return {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name not in excluded}


def _export_rows(db: Session, model: Any, candidate_id: uuid.UUID) -> list[dict[str, Any]]:
    return [
        _row_dict(row)
        for row in db.scalars(select(model).where(model.candidate_id == candidate_id)).all()
    ]


def _read_private_object(key: str) -> bytes:
    try:
        from ... import storage
    except ImportError as exc:
        raise RuntimeError("object storage support is not installed") from exc
    return storage.get_private(key)


def _delete_private_object(key: str) -> None:
    try:
        from ... import storage
    except ImportError as exc:
        raise RuntimeError("object storage support is not installed") from exc
    storage.purge_private(key)


def build_candidate_export(db: Session, user: User) -> BinaryIO:
    """Create a seekable ZIP archive; the caller owns and must close the returned file."""
    if getattr(user.role, "value", user.role) != "candidate":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="candidate accounts only")
    candidate = db.scalar(select(Candidate).where(Candidate.user_id == user.id))
    archive_file = tempfile.SpooledTemporaryFile(max_size=EXPORT_SPILL_BYTES, mode="w+b")
    try:
        with zipfile.ZipFile(archive_file, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            data: dict[str, Any] = {
                "schema_version": 1,
                "exported_at": datetime.now(UTC).isoformat(),
                "account": {
                    "id": user.id,
                    "email": user.email,
                    "phone": user.phone,
                    "preferred_language": user.preferred_language,
                    "created_at": user.created_at,
                },
                "candidate_profile": None,
                "candidate_pii": None,
                "skills": [],
                "experiences": [],
                "educations": [],
                "desired_occupations": [],
                "certifications": [],
                "mock_interviews": [],
                "onboarding_conversations": [],
                "onboarding_sessions": [],
                "applications": [],
                "matches": [],
                "skill_gaps": [],
                "roadmaps": [],
                "roadmap_items": [],
                "documents": [],
            }
            if candidate is not None:
                candidate_id = candidate.id
                data["candidate_profile"] = _row_dict(candidate)
                pii = db.get(CandidatePII, candidate_id)
                if pii is not None:
                    data["candidate_pii"] = _row_dict(pii, exclude={"photo"})
                    if pii.photo:
                        archive.writestr("candidate/photo.jpg", pii.photo)

                data["skills"] = _export_rows(db, CandidateSkill, candidate_id)
                data["experiences"] = _export_rows(db, CandidateExperience, candidate_id)
                data["educations"] = _export_rows(db, CandidateEducation, candidate_id)
                data["desired_occupations"] = _export_rows(db, CandidateDesiredOccupation, candidate_id)
                data["certifications"] = _export_rows(db, CandidateCertification, candidate_id)
                data["mock_interviews"] = _export_rows(db, MockInterviewSession, candidate_id)
                data["onboarding_conversations"] = _export_rows(db, ConversationSession, candidate_id)

                applications = db.scalars(select(Application).where(Application.candidate_id == candidate_id)).all()
                data["applications"] = [
                    {
                        "application": _row_dict(application),
                        "job_offer": (
                            _row_dict(offer)
                            if (offer := db.get(JobOffer, application.job_offer_id)) is not None
                            else None
                        ),
                    }
                    for application in applications
                ]

                matches = db.scalars(select(MatchResult).where(MatchResult.candidate_id == candidate_id)).all()
                match_ids = [item.id for item in matches]
                data["matches"] = [_row_dict(item) for item in matches]
                if match_ids:
                    data["skill_gaps"] = [
                        _row_dict(item)
                        for item in db.scalars(select(SkillGap).where(SkillGap.match_result_id.in_(match_ids))).all()
                    ]

                roadmaps = db.scalars(select(Roadmap).where(Roadmap.candidate_id == candidate_id)).all()
                roadmap_ids = [item.id for item in roadmaps]
                data["roadmaps"] = [_row_dict(item) for item in roadmaps]
                if roadmap_ids:
                    data["roadmap_items"] = [
                        _row_dict(item)
                        for item in db.scalars(select(RoadmapItem).where(RoadmapItem.roadmap_id.in_(roadmap_ids))).all()
                    ]

                documents = db.scalars(
                    select(Document).where(
                        (Document.candidate_id == candidate_id) | (Document.owner_user_id == user.id)
                    )
                ).all()
                settings = get_settings()
                for document in documents:
                    bucket, separator, key = document.storage_path.partition("/")
                    if not separator or not key or bucket != settings.s3_bucket:
                        raise RuntimeError(f"Document {document.id} has an invalid or unavailable storage path")
                    payload = _read_private_object(key)
                    archive.writestr(f"candidate/documents/{document.id}.bin", payload)
                    data["documents"].append(
                        {
                            **_row_dict(document, exclude={"storage_path", "owner_user_id"}),
                            "archive_path": f"candidate/documents/{document.id}.bin",
                        }
                    )

            data["onboarding_sessions"] = [
                _row_dict(session)
                for session in db.scalars(
                    select(CandidateOnboardingSession).where(CandidateOnboardingSession.user_id == user.id)
                ).all()
            ]
            archive.writestr(
                "data.json",
                json.dumps(data, ensure_ascii=False, indent=2, default=_json_value).encode("utf-8"),
            )
        archive_file.seek(0)
        return archive_file
    except Exception:
        archive_file.close()
        raise


def _private_storage_key(document: Document) -> str:
    bucket, separator, key = document.storage_path.partition("/")
    if not separator or not key or bucket != get_settings().s3_bucket:
        raise RuntimeError(f"Document {document.id} has an invalid or unavailable storage path")
    return key


def request_candidate_deletion(db: Session, user: User) -> datetime:
    """Disable the account, remove direct identifiers, and schedule the candidate purge."""
    if getattr(user.role, "value", user.role) != "candidate" or any(
        role != "candidate" for role in (user.roles or [])
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="candidate accounts only")

    requested_at = datetime.now(UTC)
    candidate = db.scalar(select(Candidate).where(Candidate.user_id == user.id))
    documents = []
    if candidate is not None:
        documents = db.scalars(select(Document).where(Document.candidate_id == candidate.id)).all()
    documents.extend(
        db.scalars(select(Document).where(Document.owner_user_id == user.id)).all()
    )
    seen_document_ids: set[uuid.UUID] = set()
    for document in documents:
        if document.id in seen_document_ids:
            continue
        _delete_private_object(_private_storage_key(document))
        seen_document_ids.add(document.id)

    for document in documents:
        if document.id not in seen_document_ids:
            continue
        if candidate is not None:
            db.query(CandidateCertification).filter(CandidateCertification.document_id == document.id).delete(
                synchronize_session=False
            )
        db.delete(document)

    if candidate is not None:
        db.query(CandidateCertification).filter(CandidateCertification.candidate_id == candidate.id).delete(
            synchronize_session=False
        )
        db.query(NotificationOutbox).filter(NotificationOutbox.candidate_id == candidate.id).delete(
            synchronize_session=False
        )
        db.query(Application).filter(Application.candidate_id == candidate.id).update(
            {
                Application.cover_note: None,
                Application.employer_contact_consent_at: None,
            },
            synchronize_session=False,
        )
        pii = db.get(CandidatePII, candidate.id)
        if pii is not None:
            pii.full_name = None
            pii.email = None
            pii.phone = None
            pii.date_of_birth = None
            pii.gender = None
            pii.address = None
            pii.photo = None

        candidate.summary = None
        candidate.service_offer = None
        candidate.raw_profile = None
        candidate.deleted_at = requested_at
        for experience in db.scalars(
            select(CandidateExperience).where(CandidateExperience.candidate_id == candidate.id)
        ).all():
            experience.employer_name = None
            experience.description = None
        for education in db.scalars(
            select(CandidateEducation).where(CandidateEducation.candidate_id == candidate.id)
        ).all():
            education.institution = None
        db.query(ConversationSession).filter(ConversationSession.candidate_id == candidate.id).delete(
            synchronize_session=False
        )
        db.query(MockInterviewSession).filter(MockInterviewSession.candidate_id == candidate.id).delete(
            synchronize_session=False
        )

    db.query(AuthIdentity).filter(AuthIdentity.user_id == user.id).delete(synchronize_session=False)
    db.query(AccountActionToken).filter(AccountActionToken.user_id == user.id).delete(synchronize_session=False)
    db.query(CandidateOnboardingSession).filter(CandidateOnboardingSession.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(NotificationOutbox).filter(NotificationOutbox.recipient_email == user.email).delete(
        synchronize_session=False
    )
    db.query(AuditLog).filter(AuditLog.actor_user_id == user.id).update(
        {AuditLog.actor_user_id: None, AuditLog.entity_id: None, AuditLog.payload: {}},
        synchronize_session=False,
    )
    if candidate is not None:
        db.query(AuditLog).filter(AuditLog.entity_id == str(candidate.id)).update(
            {AuditLog.entity_id: None, AuditLog.payload: {}},
            synchronize_session=False,
        )
    db.query(AnalyticsEvent).filter(AnalyticsEvent.actor_user_id == user.id).update(
        {AnalyticsEvent.actor_user_id: None},
        synchronize_session=False,
    )

    user.is_active = False
    user.deletion_requested_at = requested_at
    user.email = f"deleted-{user.id}@example.invalid"
    user.phone = None
    user.password_hash = None
    user.email_verified = False
    user.last_login_at = None
    db.commit()
    return requested_at + timedelta(days=DELETION_RETENTION_DAYS)


def purge_expired_candidate_accounts(now: datetime | None = None) -> int:
    """Purge expired candidate records, retrying individual failures on the next pass."""
    from ...database import SessionLocal

    current_time = now or datetime.now(UTC)
    cutoff = current_time - timedelta(days=DELETION_RETENTION_DAYS)
    purged = 0
    with SessionLocal() as lookup:
        user_ids = list(
            lookup.scalars(select(User.id).where(User.deletion_requested_at <= cutoff)).all()
        )

    for user_id in user_ids:
        try:
            with SessionLocal() as db:
                user = db.scalar(
                    select(User)
                    .where(User.id == user_id, User.deletion_requested_at <= cutoff)
                    .with_for_update(skip_locked=True)
                )
                if user is None:
                    continue
                candidates = db.scalars(select(Candidate).where(Candidate.user_id == user_id)).all()
                for candidate in candidates:
                    documents = db.scalars(select(Document).where(Document.candidate_id == candidate.id)).all()
                    for document in documents:
                        _delete_private_object(_private_storage_key(document))
                    candidate.user_id = None
                    db.delete(candidate)
                    db.flush()

                for model, column in (
                    (AuditLog, AuditLog.actor_user_id),
                    (AnalyticsEvent, AnalyticsEvent.actor_user_id),
                    (Document, Document.owner_user_id),
                    (IngestionJob, IngestionJob.triggered_by),
                ):
                    db.execute(update(model).where(column == user_id).values({column.key: None}))
                db.delete(user)
                db.commit()
                purged += 1
        except Exception:
            logger.exception("Could not purge expired candidate account %s", user_id)
    return purged


async def run_candidate_deletion_retention_loop() -> None:
    import asyncio

    while True:
        try:
            purged = await asyncio.to_thread(purge_expired_candidate_accounts)
            if purged:
                logger.info("Purged %s expired candidate account(s)", purged)
        except Exception:
            logger.exception("Candidate data retention cleanup failed")
        await asyncio.sleep(3600)
