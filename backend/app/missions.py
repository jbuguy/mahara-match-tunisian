"""Independent mission and proposal workflows, separate from job applications."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.audit import record_audit_event
from app.database import get_session
from app.dependencies import assert_organisation_member, get_current_user
from app.models import (
    Mission, MissionProposal, MissionProposalStatus, MissionStatus,
    MissionStatusHistory, Organisation, OrganisationMembership, OrganisationType, Role, User,
)
from app.schemas import (
    MissionCreate, MissionProposalCreate, MissionProposalResponse,
    MissionProposalStatusUpdate, MissionResponse, MissionSearchPage,
    MissionStatusHistoryResponse, MissionStatusUpdate, PublicMissionResponse,
)

router = APIRouter(tags=["missions"])


def _public(mission: Mission) -> PublicMissionResponse:
    return PublicMissionResponse.model_validate(mission)


def _publisher_access(mission: Mission, user: User, session: Session) -> bool:
    if mission.organisation_id:
        if user.role not in {Role.EMPLOYER, Role.TRAINING_PROVIDER}:
            return False
        try:
            assert_organisation_member(user, organisation_id=mission.organisation_id, session=session)
            return True
        except HTTPException:
            return False
    return mission.publisher_user_id == user.id


@router.get("/public/missions", response_model=MissionSearchPage, tags=["public discovery"])
def search_missions(
    q: str | None = Query(default=None, min_length=1, max_length=160),
    location: str | None = Query(default=None, min_length=1, max_length=120),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    skill: str | None = Query(default=None, min_length=1, max_length=60),
    work_mode: str | None = Query(default=None, min_length=1, max_length=30),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> MissionSearchPage:
    filters = [Mission.status == MissionStatus.PUBLISHED]
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(Mission.title.ilike(pattern) | Mission.description.ilike(pattern) | Mission.category.ilike(pattern) | cast(Mission.required_skills, String).ilike(pattern))
    if location:
        filters.append(Mission.location.ilike(f"%{location.strip()}%"))
    if category:
        filters.append(Mission.category.ilike(f"%{category.strip()}%"))
    if skill:
        filters.append(cast(Mission.required_skills, String).ilike(f"%{skill.strip()}%"))
    if work_mode:
        filters.append(Mission.work_mode == work_mode)
    query = select(Mission).where(*filters)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(query.order_by(Mission.created_at.desc(), Mission.id).offset(offset).limit(limit))
    return MissionSearchPage(items=[_public(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/public/missions/{mission_id}", response_model=PublicMissionResponse, tags=["public discovery"])
def get_public_mission(mission_id: str, session: Session = Depends(get_session)) -> PublicMissionResponse:
    mission = session.scalar(select(Mission).where(Mission.id == mission_id, Mission.status == MissionStatus.PUBLISHED))
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found.")
    return _public(mission)


@router.post("/missions", response_model=MissionResponse, status_code=status.HTTP_201_CREATED)
def create_mission(request: MissionCreate, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MissionResponse:
    if user.role in {Role.MINISTRY_ADMIN, Role.OPERATOR}:
        raise HTTPException(status_code=403, detail="This account cannot publish missions.")
    if request.organisation_id:
        assert_organisation_member(user, organisation_id=request.organisation_id, session=session)
        organisation = session.get(Organisation, request.organisation_id)
        if organisation is None or organisation.organisation_type != OrganisationType.EMPLOYER:
            raise HTTPException(status_code=403, detail="Missions can only be published for an employer organisation.")
    values = request.model_dump(exclude={"organisation_id"})
    mission = Mission(publisher_user_id=user.id, organisation_id=request.organisation_id, **values)
    session.add(mission)
    session.flush()
    session.add(MissionStatusHistory(mission_id=mission.id, changed_by_user_id=user.id, new_status=MissionStatus.DRAFT))
    record_audit_event(session, action="mission.created", actor=user, resource_type="mission", resource_id=mission.id)
    session.commit()
    session.refresh(mission)
    return MissionResponse.model_validate(mission)


@router.get("/missions/me", response_model=list[MissionResponse])
def my_missions(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[MissionResponse]:
    filters = [Mission.publisher_user_id == user.id]
    if user.role == Role.EMPLOYER:
        employer_orgs = select(OrganisationMembership.organisation_id).join(Organisation, Organisation.id == OrganisationMembership.organisation_id).where(OrganisationMembership.user_id == user.id, Organisation.organisation_type == OrganisationType.EMPLOYER)
        filters.append(Mission.organisation_id.in_(employer_orgs))
    missions = session.scalars(select(Mission).where(or_(*filters)).order_by(Mission.created_at.desc()))
    return [MissionResponse.model_validate(item) for item in missions]


@router.put("/missions/{mission_id}", response_model=MissionResponse)
def update_mission(mission_id: str, request: MissionCreate, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MissionResponse:
    mission = session.get(Mission, mission_id)
    if mission is None or not _publisher_access(mission, user, session):
        raise HTTPException(status_code=404, detail="Mission not found.")
    if mission.status != MissionStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft missions can be edited.")
    if request.organisation_id != mission.organisation_id:
        raise HTTPException(status_code=409, detail="Mission ownership cannot be changed after creation.")
    for key, value in request.model_dump(exclude={"organisation_id"}).items():
        setattr(mission, key, value)
    mission.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(mission)
    return MissionResponse.model_validate(mission)


@router.patch("/missions/{mission_id}/status", response_model=MissionResponse)
def update_mission_status(mission_id: str, request: MissionStatusUpdate, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MissionResponse:
    mission = session.get(Mission, mission_id)
    if mission is None or not _publisher_access(mission, user, session):
        raise HTTPException(status_code=404, detail="Mission not found.")
    transitions = {
        MissionStatus.DRAFT: {MissionStatus.PUBLISHED, MissionStatus.CANCELLED, MissionStatus.ARCHIVED},
        MissionStatus.PUBLISHED: {MissionStatus.IN_PROGRESS, MissionStatus.CANCELLED, MissionStatus.EXPIRED, MissionStatus.ARCHIVED},
        MissionStatus.IN_PROGRESS: {MissionStatus.COMPLETED, MissionStatus.CANCELLED},
        MissionStatus.COMPLETED: set(), MissionStatus.CANCELLED: set(), MissionStatus.EXPIRED: set(), MissionStatus.ARCHIVED: set(),
    }
    next_status = MissionStatus(request.status)
    if next_status not in transitions[mission.status]:
        raise HTTPException(status_code=409, detail=f"Cannot change mission from {mission.status.value} to {next_status.value}.")
    previous = mission.status
    mission.status = next_status
    mission.updated_at = datetime.now(timezone.utc)
    session.add(MissionStatusHistory(mission_id=mission.id, changed_by_user_id=user.id, previous_status=previous, new_status=next_status))
    record_audit_event(session, action="mission.status_updated", actor=user, resource_type="mission", resource_id=mission.id, details={"from": previous.value, "to": next_status.value})
    session.commit()
    session.refresh(mission)
    return MissionResponse.model_validate(mission)


@router.get("/missions/{mission_id}/status-history", response_model=list[MissionStatusHistoryResponse])
def mission_status_history(mission_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[MissionStatusHistoryResponse]:
    mission = session.get(Mission, mission_id)
    if mission is None or not _publisher_access(mission, user, session):
        raise HTTPException(status_code=404, detail="Mission not found.")
    rows = session.scalars(select(MissionStatusHistory).where(MissionStatusHistory.mission_id == mission_id).order_by(MissionStatusHistory.created_at))
    return [MissionStatusHistoryResponse(previous_status=row.previous_status.value if row.previous_status else None, new_status=row.new_status.value, created_at=row.created_at) for row in rows]


@router.post("/missions/{mission_id}/proposals", response_model=MissionProposalResponse, status_code=status.HTTP_201_CREATED)
def submit_proposal(mission_id: str, request: MissionProposalCreate, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MissionProposalResponse:
    mission = session.get(Mission, mission_id)
    if mission is None or mission.status != MissionStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Published mission not found.")
    if mission.publisher_user_id == user.id:
        raise HTTPException(status_code=409, detail="You cannot submit a proposal to your own mission.")
    if user.role in {Role.MINISTRY_ADMIN, Role.OPERATOR}:
        raise HTTPException(status_code=403, detail="This account cannot submit proposals.")
    proposal = MissionProposal(mission_id=mission_id, provider_user_id=user.id, **request.model_dump())
    session.add(proposal)
    try:
        session.commit()
    except Exception as error:
        session.rollback()
        if session.scalar(select(MissionProposal.id).where(MissionProposal.mission_id == mission_id, MissionProposal.provider_user_id == user.id)):
            raise HTTPException(status_code=409, detail="You already submitted a proposal for this mission.") from error
        raise
    session.refresh(proposal)
    record_audit_event(session, action="mission.proposal_submitted", actor=user, resource_type="mission_proposal", resource_id=proposal.id)
    session.commit()
    return MissionProposalResponse.model_validate(proposal)


@router.get("/missions/{mission_id}/proposals", response_model=list[MissionProposalResponse])
def mission_proposals(mission_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[MissionProposalResponse]:
    mission = session.get(Mission, mission_id)
    if mission is None or not _publisher_access(mission, user, session):
        raise HTTPException(status_code=404, detail="Mission not found.")
    proposals = session.scalars(select(MissionProposal).where(MissionProposal.mission_id == mission_id).order_by(MissionProposal.created_at))
    return [MissionProposalResponse.model_validate(item) for item in proposals]


@router.get("/mission-proposals/me", response_model=list[MissionProposalResponse])
def my_proposals(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[MissionProposalResponse]:
    proposals = session.scalars(select(MissionProposal).where(MissionProposal.provider_user_id == user.id).order_by(MissionProposal.created_at.desc()))
    return [MissionProposalResponse.model_validate(item) for item in proposals]


@router.patch("/missions/{mission_id}/proposals/{proposal_id}", response_model=MissionProposalResponse)
def update_proposal_status(mission_id: str, proposal_id: str, request: MissionProposalStatusUpdate, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MissionProposalResponse:
    mission = session.get(Mission, mission_id)
    proposal = session.scalar(select(MissionProposal).where(MissionProposal.id == proposal_id, MissionProposal.mission_id == mission_id))
    if mission is None or proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    desired = MissionProposalStatus(request.status)
    if proposal.provider_user_id == user.id and desired == MissionProposalStatus.WITHDRAWN:
        allowed = proposal.status in {MissionProposalStatus.SUBMITTED, MissionProposalStatus.UNDER_REVIEW}
    elif _publisher_access(mission, user, session):
        allowed = proposal.status in {MissionProposalStatus.SUBMITTED, MissionProposalStatus.UNDER_REVIEW} and desired in {MissionProposalStatus.UNDER_REVIEW, MissionProposalStatus.ACCEPTED, MissionProposalStatus.REJECTED}
    else:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    if not allowed:
        raise HTTPException(status_code=409, detail="This proposal status transition is not allowed.")
    if desired == MissionProposalStatus.ACCEPTED:
        others = session.scalars(select(MissionProposal).where(MissionProposal.mission_id == mission_id, MissionProposal.id != proposal_id, MissionProposal.status.in_([MissionProposalStatus.SUBMITTED, MissionProposalStatus.UNDER_REVIEW])))
        for other in others:
            other.status = MissionProposalStatus.REJECTED
    proposal.status = desired
    proposal.updated_at = datetime.now(timezone.utc)
    record_audit_event(session, action="mission.proposal_status_updated", actor=user, resource_type="mission_proposal", resource_id=proposal.id, details={"to": desired.value})
    session.commit()
    session.refresh(proposal)
    return MissionProposalResponse.model_validate(proposal)
