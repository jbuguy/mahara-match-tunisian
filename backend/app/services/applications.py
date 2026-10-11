"""Business rules and WP1 contract mapping for candidate applications."""

import uuid

from mahara_data.db.models.candidates import Candidate
from mahara_data.db.models.employers import (
    Application,
    Employer,
    HiringFeedback,
    JobOffer,
)
from mahara_data.db.models.matching import MatchResult
from mahara_data.enums import ApplicationStatus, HiringDecision, OfferStatus
from mahara_data.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
)
from mahara_data.schemas.application import (
    HiringFeedback as HiringFeedbackContract,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..repositories import applications as repository


class ApplicationWorkflowError(Exception):
    """A lifecycle error suitable for mapping to an API response."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _application_payload(application: Application, offer: JobOffer, match: MatchResult | None = None) -> dict:
    contract = ApplicationRead(
        application_id=application.id,
        candidate_id=application.candidate_id,
        job_offer_id=application.job_offer_id,
        match_id=application.match_result_id,
        score_global=match.score_global if match is not None else None,
        status=application.status,
        applied_at=application.applied_at,
        updated_at=application.updated_at,
    )
    return {"title": offer.title, **contract.model_dump(mode="json")}


def list_candidate_applications(db: Session, *, user_id: uuid.UUID) -> list[dict]:
    candidate = repository.get_candidate_for_user(db, user_id)
    if candidate is None:
        raise ApplicationWorkflowError(404, "Candidate profile not found")
    return [
        _application_payload(application, offer, match)
        for application, offer, match in repository.list_candidate_applications(db, candidate.id)
    ]


def create_candidate_application(
    db: Session,
    *,
    user_id: uuid.UUID,
    job_offer_id: uuid.UUID,
    cover_note: str | None = None,
) -> dict:
    """Apply using the authenticated candidate and their current match snapshot."""
    candidate = repository.get_candidate_for_user(db, user_id)
    if candidate is None:
        raise ApplicationWorkflowError(404, "Candidate profile not found")

    offer = repository.get_offer(db, job_offer_id)
    if offer is None or offer.status is not OfferStatus.PUBLISHED:
        raise ApplicationWorkflowError(404, "Published offer not found")

    match = repository.get_current_match(db, candidate.id, offer.id)
    if match is None:
        raise ApplicationWorkflowError(409, "View your current matches before applying")

    request = ApplicationCreate(candidate_id=candidate.id, job_offer_id=offer.id, cover_note=cover_note)
    application = Application(
        candidate_id=request.candidate_id,
        job_offer_id=offer.id,
        match_result_id=match.id,
        cover_note=request.cover_note,
    )
    try:
        repository.insert_application(db, application)
    except IntegrityError:
        raise ApplicationWorkflowError(409, "You have already applied to this offer") from None
    return _application_payload(application, offer, match)


def list_employer_applications(db: Session, *, employer: Employer) -> list[dict]:
    """Return applications and application-authorized candidate contact details."""
    rows = repository.list_employer_applications(db, employer.id)
    repository.audit_candidate_identity_reads(
        db,
        actor_user_id=employer.user_id,
        employer_id=employer.id,
        applications=rows,
    )
    return [
        {
            "application_id": str(application.id),
            "candidate_id": str(candidate.id),
            "candidate_name": pii.full_name if pii is not None else None,
            "candidate_email": pii.email if pii is not None else None,
            "candidate_phone": pii.phone if pii is not None else None,
            "match_id": str(application.match_result_id) if application.match_result_id else None,
            "score_global": float(match.score_global) if match is not None else None,
            "job_offer_id": str(offer.id),
            "title": offer.title,
            "status": application.status.value,
            "applied_at": application.applied_at.isoformat(),
        }
        for application, offer, candidate, pii, match in rows
    ]


def record_employer_decision(
    db: Session,
    *,
    employer: Employer,
    application_id: uuid.UUID,
    decision: HiringDecision,
    reason_code: str | None = None,
    match_quality: int | None = None,
    comment: str | None = None,
) -> Application:
    """Validate and persist a hiring decision for an employer-owned offer."""
    application = repository.get_application_for_employer(db, application_id, employer.id)
    if application is None:
        raise ApplicationWorkflowError(404, "Application not found")
    if application.status in {ApplicationStatus.HIRED, ApplicationStatus.REJECTED}:
        raise ApplicationWorkflowError(409, "This application already has a final decision")

    feedback = HiringFeedbackContract(
        application_id=application.id,
        employer_id=employer.id,
        decision=decision,
        reason_code=reason_code,
        match_quality=match_quality,
        comment=comment,
    )
    application.status = {
        HiringDecision.HIRED: ApplicationStatus.HIRED,
        HiringDecision.SHORTLISTED: ApplicationStatus.SHORTLISTED,
        HiringDecision.REJECTED: ApplicationStatus.REJECTED,
        HiringDecision.NO_SHOW: ApplicationStatus.REJECTED,
    }[feedback.decision]
    repository.insert_hiring_feedback(
        db,
        HiringFeedback(
            application_id=feedback.application_id,
            employer_id=feedback.employer_id,
            decision=feedback.decision,
            reason_code=feedback.reason_code,
            match_quality=feedback.match_quality,
            comment=feedback.comment,
        ),
    )
    db.refresh(application)
    return application
