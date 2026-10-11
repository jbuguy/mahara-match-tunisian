import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mahara_data.db.models.employers import Employer
from mahara_data.enums import HiringDecision

from .services.applications import (
    ApplicationWorkflowError,
    create_candidate_application,
    list_candidate_applications as get_candidate_applications,
    list_employer_applications as get_employer_applications,
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
