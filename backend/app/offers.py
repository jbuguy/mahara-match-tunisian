"""Candidate-facing published offer endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .services.applications import ApplicationWorkflowError
from .services.offers import list_candidate_offers


def create_offer_router(get_db: Any, get_current_user: Any) -> APIRouter:
    router = APIRouter(tags=["offers"])

    @router.get("/api/v1/me/offers")
    def get_candidate_offers(
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ) -> list[dict]:
        try:
            return list_candidate_offers(db, user_id=UUID(str(user.id)))
        except ApplicationWorkflowError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    return router
