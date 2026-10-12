import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from mahara_data.db.models.employers import Application, Employer, JobOffer
from mahara_data.db.models.matching import MatchResult
from mahara_data.enums import ApplicationStatus, HiringDecision

from .services.applications import (
    ApplicationWorkflowError,
    create_candidate_application,
    list_candidate_applications as get_candidate_applications,
    list_employer_applications as get_employer_applications,
    get_employer_application_detail,
    record_employer_decision as save_employer_decision,
)


class ApplicationApplyRequest(BaseModel):
    job_offer_id: uuid.UUID
    cover_note: str | None = Field(default=None, max_length=2000)


class EmployerDecision(BaseModel):
    decision: HiringDecision
    reason_code: str | None = Field(default=None, max_length=64)
    match_quality: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


def create_application_router(get_db: Any, get_current_user: Any, get_current_employer: Any) -> APIRouter:
    router = APIRouter(tags=["applications"])

    @router.get("/api/v1/me/applications")
    def list_candidate_applications(
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        try:
            return get_candidate_applications(db, user_id=user.id)
        except ApplicationWorkflowError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    @router.post("/api/v1/me/applications", status_code=201)
    def apply_to_offer(
        payload: ApplicationApplyRequest,
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        try:
            return create_candidate_application(
                db,
                user_id=user.id,
                job_offer_id=payload.job_offer_id,
                cover_note=payload.cover_note,
            )
        except ApplicationWorkflowError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    @router.get("/api/v1/employer/applications")
    def list_employer_applications(
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        return get_employer_applications(db, employer=employer)

    @router.get("/api/v1/employer/applications/{application_id}")
    def get_employer_application(
        application_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        try:
            return get_employer_application_detail(db, employer=employer, application_id=application_id)
        except ApplicationWorkflowError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    @router.get("/api/v1/employer/offers")
    def list_employer_offers(
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        rows = (
            db.query(
                JobOffer,
                func.count(Application.id),
                func.sum(case((Application.status == ApplicationStatus.SUBMITTED, 1), else_=0)),
                func.sum(case((Application.status == ApplicationStatus.SHORTLISTED, 1), else_=0)),
                func.sum(case((Application.status == ApplicationStatus.HIRED, 1), else_=0)),
                func.sum(case((Application.status == ApplicationStatus.REJECTED, 1), else_=0)),
                func.max(MatchResult.score_global),
            )
            .outerjoin(Application, Application.job_offer_id == JobOffer.id)
            .outerjoin(MatchResult, MatchResult.id == Application.match_result_id)
            .filter(JobOffer.employer_id == employer.id)
            .group_by(JobOffer.id)
            .order_by(JobOffer.published_at.desc().nullslast(), JobOffer.created_at.desc())
            .all()
        )
        return [
            {
                "job_offer_id": str(offer.id),
                "title": offer.title,
                "status": offer.status.value,
                "published_at": offer.published_at.isoformat() if offer.published_at else None,
                "expires_at": offer.expires_at.isoformat() if offer.expires_at else None,
                "applications_count": applications or 0,
                "submitted_count": submitted or 0,
                "shortlisted_count": shortlisted or 0,
                "hired_count": hired or 0,
                "rejected_count": rejected or 0,
                "top_match_score": float(top_score) if top_score is not None else None,
            }
            for offer, applications, submitted, shortlisted, hired, rejected, top_score in rows
        ]

    @router.patch("/api/v1/employer/applications/{application_id}")
    def record_employer_decision(
        application_id: uuid.UUID,
        payload: EmployerDecision,
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        try:
            application = save_employer_decision(
                db,
                employer=employer,
                application_id=application_id,
                decision=payload.decision,
                reason_code=payload.reason_code,
                match_quality=payload.match_quality,
                comment=payload.comment,
            )
        except ApplicationWorkflowError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail) from error
        return {"application_id": str(application.id), "status": application.status.value}

    return router
