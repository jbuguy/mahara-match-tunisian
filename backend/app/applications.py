import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mahara_data.db.models.candidates import Candidate, CandidatePII
from mahara_data.db.models.employers import Application, Employer, HiringFeedback, JobOffer
from mahara_data.db.models.matching import MatchResult
from mahara_data.db.models.platform import AuditLog
from mahara_data.enums import ApplicationStatus, HiringDecision, OfferStatus
from mahara_data.schemas.application import ApplicationCreate as WP1ApplicationCreate
from mahara_data.schemas.application import ApplicationRead as WP1ApplicationRead
from mahara_data.schemas.application import HiringFeedback as WP1HiringFeedback


class ApplicationCreate(BaseModel):
    job_offer_id: uuid.UUID
    cover_note: str | None = Field(default=None, max_length=2000)


class EmployerDecision(BaseModel):
    decision: HiringDecision
    reason_code: str | None = Field(default=None, max_length=64)
    match_quality: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


def _application_payload(application: Application, offer: JobOffer, match: MatchResult | None = None):
    contract = WP1ApplicationRead(
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


def create_application_router(get_db: Any, get_current_user: Any, get_current_employer: Any) -> APIRouter:
    router = APIRouter(tags=["applications"])

    @router.get("/api/v1/me/applications")
    def list_candidate_applications(
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        rows = (
            db.query(Application, JobOffer, MatchResult)
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .outerjoin(MatchResult, MatchResult.id == Application.match_result_id)
            .filter(Application.candidate_id == candidate.id)
            .order_by(Application.applied_at.desc())
            .all()
        )
        return [_application_payload(application, offer, match) for application, offer, match in rows]

    @router.post("/api/v1/me/applications", status_code=201)
    def apply_to_offer(
        payload: ApplicationCreate,
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        offer = db.get(JobOffer, payload.job_offer_id)
        if offer is None or offer.status is not OfferStatus.PUBLISHED:
            raise HTTPException(status_code=404, detail="Published offer not found")
        match = (
            db.query(MatchResult)
            .filter(
                MatchResult.candidate_id == candidate.id,
                MatchResult.job_offer_id == offer.id,
                MatchResult.is_current.is_(True),
            )
            .order_by(MatchResult.computed_at.desc())
            .first()
        )
        if match is None:
            raise HTTPException(status_code=409, detail="View your current matches before applying")
        request_contract = WP1ApplicationCreate(
            candidate_id=candidate.id,
            job_offer_id=payload.job_offer_id,
            cover_note=payload.cover_note,
        )
        application = Application(
            candidate_id=request_contract.candidate_id,
            job_offer_id=offer.id,
            match_result_id=match.id,
            cover_note=request_contract.cover_note,
        )
        db.add(application)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="You have already applied to this offer") from None
        db.refresh(application)
        return _application_payload(application, offer, match)

    @router.get("/api/v1/employer/applications")
    def list_employer_applications(
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        rows = (
            db.query(Application, JobOffer, Candidate, CandidatePII, MatchResult)
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .outerjoin(CandidatePII, CandidatePII.candidate_id == Candidate.id)
            .outerjoin(MatchResult, MatchResult.id == Application.match_result_id)
            .filter(JobOffer.employer_id == employer.id)
            .order_by(Application.applied_at.desc())
            .all()
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

    @router.patch("/api/v1/employer/applications/{application_id}")
    def record_employer_decision(
        application_id: uuid.UUID,
        payload: EmployerDecision,
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        row = (
            db.query(Application, JobOffer)
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .filter(Application.id == application_id, JobOffer.employer_id == employer.id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Application not found")
        application, _offer = row
        feedback = WP1HiringFeedback(
            application_id=application.id,
            employer_id=employer.id,
            decision=payload.decision,
            reason_code=payload.reason_code,
            match_quality=payload.match_quality,
            comment=payload.comment,
        )
        application.status = {
            HiringDecision.HIRED: ApplicationStatus.HIRED,
            HiringDecision.SHORTLISTED: ApplicationStatus.SHORTLISTED,
            HiringDecision.REJECTED: ApplicationStatus.REJECTED,
            HiringDecision.NO_SHOW: ApplicationStatus.REJECTED,
        }[feedback.decision]
        db.add(
            HiringFeedback(
                application_id=feedback.application_id,
                employer_id=feedback.employer_id,
                decision=feedback.decision,
                reason_code=feedback.reason_code,
                match_quality=feedback.match_quality,
                comment=feedback.comment,
            )
        )
        db.commit()
        return {"application_id": str(application.id), "status": application.status.value}

    return router