"""Organisation-scoped employer workforce planning session API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_audit_event
from app.database import get_session
from app.dependencies import require_role
from app.models import (
    EmployerPlanningSession,
    Organisation,
    OrganisationMembership,
    OrganisationType,
    PlanningSessionStatus,
    Role,
    User,
)
from app.schemas import PlanningSessionCreateRequest, PlanningSessionResponse, PlanningSessionUpdateRequest


router = APIRouter(tags=["employer planning"])


def _organisation_for_employer(session: Session, user: User) -> Organisation:
    organisation = session.scalar(
        select(Organisation)
        .join(OrganisationMembership, OrganisationMembership.organisation_id == Organisation.id)
        .where(
            OrganisationMembership.user_id == user.id,
            Organisation.organisation_type == OrganisationType.EMPLOYER,
        )
        .order_by(Organisation.created_at, Organisation.id)
    )
    if organisation is None:
        raise HTTPException(status_code=404, detail="No employer organisation is linked to this account.")
    return organisation


def _session_for_organisation(
    session: Session, organisation_id: str, session_id: str
) -> EmployerPlanningSession:
    planning = session.scalar(
        select(EmployerPlanningSession).where(
            EmployerPlanningSession.id == session_id,
            EmployerPlanningSession.organisation_id == organisation_id,
        )
    )
    if planning is None:
        raise HTTPException(status_code=404, detail="Planning session not found.")
    return planning


def _response(planning: EmployerPlanningSession) -> PlanningSessionResponse:
    return PlanningSessionResponse.model_validate(planning)


@router.get("/employer/planning-sessions", response_model=list[PlanningSessionResponse])
def list_planning_sessions(
    user: User = Depends(require_role(Role.EMPLOYER)),
    session: Session = Depends(get_session),
) -> list[PlanningSessionResponse]:
    organisation = _organisation_for_employer(session, user)
    rows = session.scalars(
        select(EmployerPlanningSession)
        .where(EmployerPlanningSession.organisation_id == organisation.id)
        .order_by(EmployerPlanningSession.updated_at.desc())
    )
    return [_response(item) for item in rows]


@router.post(
    "/employer/planning-sessions",
    response_model=PlanningSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_planning_session(
    request: PlanningSessionCreateRequest,
    user: User = Depends(require_role(Role.EMPLOYER)),
    session: Session = Depends(get_session),
) -> PlanningSessionResponse:
    organisation = _organisation_for_employer(session, user)
    now = datetime.now(timezone.utc)
    planning = EmployerPlanningSession(
        organisation_id=organisation.id,
        created_by_user_id=user.id,
        title=request.title,
        description=request.description,
        project_type=request.project_type,
        status=PlanningSessionStatus.DRAFT,
        project_summary={},
        created_at=now,
        updated_at=now,
    )
    session.add(planning)
    session.flush()
    record_audit_event(
        session,
        action="employer.planning_session.created",
        actor=user,
        resource_type="planning_session",
        resource_id=planning.id,
        details={"project_type": planning.project_type},
    )
    session.commit()
    session.refresh(planning)
    return _response(planning)


@router.get("/employer/planning-sessions/{session_id}", response_model=PlanningSessionResponse)
def get_planning_session(
    session_id: str,
    user: User = Depends(require_role(Role.EMPLOYER)),
    session: Session = Depends(get_session),
) -> PlanningSessionResponse:
    organisation = _organisation_for_employer(session, user)
    planning = _session_for_organisation(session, organisation.id, session_id)
    return _response(planning)


@router.patch("/employer/planning-sessions/{session_id}", response_model=PlanningSessionResponse)
def update_planning_session(
    session_id: str,
    request: PlanningSessionUpdateRequest,
    user: User = Depends(require_role(Role.EMPLOYER)),
    session: Session = Depends(get_session),
) -> PlanningSessionResponse:
    organisation = _organisation_for_employer(session, user)
    planning = _session_for_organisation(session, organisation.id, session_id)
    changes = request.model_dump(exclude_unset=True)
    next_status = changes.get("status")
    transitions = {
        PlanningSessionStatus.DRAFT: {PlanningSessionStatus.IN_PROGRESS, PlanningSessionStatus.ARCHIVED},
        PlanningSessionStatus.IN_PROGRESS: {PlanningSessionStatus.ANALYSIS_READY, PlanningSessionStatus.COMPLETED, PlanningSessionStatus.ARCHIVED},
        PlanningSessionStatus.ANALYSIS_READY: {PlanningSessionStatus.IN_PROGRESS, PlanningSessionStatus.COMPLETED, PlanningSessionStatus.ARCHIVED},
        PlanningSessionStatus.COMPLETED: {PlanningSessionStatus.ARCHIVED},
        PlanningSessionStatus.ARCHIVED: set(),
    }
    if next_status is not None and next_status != planning.status:
        if next_status not in transitions[planning.status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot change a planning session from {planning.status.value} to {next_status.value}.",
            )
    for field, value in changes.items():
        setattr(planning, field, value)
    planning.updated_at = datetime.now(timezone.utc)
    record_audit_event(
        session,
        action="employer.planning_session.updated",
        actor=user,
        resource_type="planning_session",
        resource_id=planning.id,
        details={"fields": sorted(changes)},
    )
    session.commit()
    session.refresh(planning)
    return _response(planning)


@router.delete("/employer/planning-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planning_session(
    session_id: str,
    user: User = Depends(require_role(Role.EMPLOYER)),
    session: Session = Depends(get_session),
) -> Response:
    organisation = _organisation_for_employer(session, user)
    planning = _session_for_organisation(session, organisation.id, session_id)
    record_audit_event(
        session,
        action="employer.planning_session.deleted",
        actor=user,
        resource_type="planning_session",
        resource_id=planning.id,
    )
    session.delete(planning)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
