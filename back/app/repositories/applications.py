"""Database access for the shared WP4/WP6 application workflow."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mahara_data.db.models.candidates import Candidate, CandidatePII
from mahara_data.db.models.employers import Application, HiringFeedback, JobOffer
from mahara_data.db.models.matching import MatchResult
from mahara_data.db.models.platform import AuditLog

from .accounts import get_candidate_for_user


def list_candidate_applications(db: Session, candidate_id: UUID):
    return (
        db.query(Application, JobOffer, MatchResult)
        .join(JobOffer, JobOffer.id == Application.job_offer_id)
        .outerjoin(MatchResult, MatchResult.id == Application.match_result_id)
        .filter(Application.candidate_id == candidate_id)
        .order_by(Application.applied_at.desc())
        .all()
    )


def list_employer_applications(db: Session, employer_id: UUID):
    return (
        db.query(Application, JobOffer, Candidate, CandidatePII, MatchResult)
        .join(JobOffer, JobOffer.id == Application.job_offer_id)
        .join(Candidate, Candidate.id == Application.candidate_id)
        .outerjoin(CandidatePII, CandidatePII.candidate_id == Candidate.id)
        .outerjoin(MatchResult, MatchResult.id == Application.match_result_id)
        .filter(JobOffer.employer_id == employer_id)
        .order_by(Application.applied_at.desc())
        .all()
    )


def get_offer(db: Session, offer_id: UUID) -> JobOffer | None:
    return db.get(JobOffer, offer_id)


def get_current_match(
    db: Session, candidate_id: UUID, offer_id: UUID
) -> MatchResult | None:
    return (
        db.query(MatchResult)
        .filter(
            MatchResult.candidate_id == candidate_id,
            MatchResult.job_offer_id == offer_id,
            MatchResult.is_current.is_(True),
        )
        .order_by(MatchResult.computed_at.desc())
        .first()
    )


def insert_application(db: Session, application: Application) -> Application:
    db.add(application)
    _commit(db)
    db.refresh(application)
    return application


def get_application_for_employer(
    db: Session, application_id: UUID, employer_id: UUID
) -> Application | None:
    return (
        db.query(Application)
        .join(JobOffer, JobOffer.id == Application.job_offer_id)
        .filter(Application.id == application_id, JobOffer.employer_id == employer_id)
        .first()
    )


def insert_hiring_feedback(db: Session, feedback: HiringFeedback) -> None:
    db.add(feedback)
    _commit(db)


def audit_candidate_identity_reads(
    db: Session,
    *,
    actor_user_id: UUID | None,
    employer_id: UUID,
    applications: list[
        tuple[Application, JobOffer, Candidate, CandidatePII | None, MatchResult | None]
    ],
) -> None:
    audited = False
    for application, offer, candidate, pii, _match in applications:
        if pii is None:
            continue
        audited = True
        db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                actor_service=None if actor_user_id else "wp4-employer-session",
                action="candidate.pii.read",
                entity_type="candidate_pii",
                entity_id=str(candidate.id),
                payload={
                    "application_id": str(application.id),
                    "job_offer_id": str(offer.id),
                    "employer_id": str(employer_id),
                },
            )
        )
    if audited:
        _commit(db)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
