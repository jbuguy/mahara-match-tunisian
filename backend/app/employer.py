"""Employer recruitment workflows with application and consent boundaries."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_audit_event, record_sensitive_read
from app.database import get_session
from app.dependencies import get_current_user, require_permission
from app.models import (
    ApplicationEvaluation,
    ApplicationNote,
    CandidateProfile,
    Conversation,
    EmployerNotification,
    EmployerNotificationPreference,
    Interview,
    InterviewFeedback,
    InterviewParticipant,
    InterviewStatus,
    JobApplication,
    JobApplicationStatus,
    JobApplicationStatusHistory,
    record_application_status_event,
    JobOffer,
    JobOfferDecisionStatus,
    JobOfferDecision,
    Organisation,
    OrganisationMembership,
    OrganisationType,
    OrganisationVerificationRequest,
    OrganisationVerificationStatus,
    Message,
    Role,
    TalentPool,
    TalentPoolMember,
    User,
)
from app.permissions import Permission
from app.schemas import (
    ApplicationEvaluationRequest,
    ApplicationEvaluationResponse,
    ApplicationNoteCreateRequest,
    ApplicationNoteResponse,
    ApplicationStatusHistoryResponse,
    CandidateDiscoveryResponse,
    ConversationResponse,
    EmployerAnalyticsResponse,
    EmployerApplicationDetailResponse,
    EmployerApplicationResponse,
    InterviewCreateRequest,
    InterviewResponse,
    InterviewStatusUpdate,
    InterviewFeedbackRequest,
    InterviewFeedbackResponse,
    MessageCreateRequest,
    MessageResponse,
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    OrganisationVerificationCreateRequest,
    OrganisationVerificationResponse,
    OrganisationVerificationReviewRequest,
    TalentPoolCreateRequest,
    TalentPoolMemberRequest,
    TalentPoolMemberResponse,
    TalentPoolResponse,
    JobOfferDecisionCreateRequest,
    JobOfferDecisionUpdateRequest,
    JobOfferDecisionResponse,
)

router = APIRouter()


def _application_for_employer(
    session: Session, application_id: str, employer_id: str
) -> tuple[JobApplication, JobOffer]:
    result = session.execute(
        select(JobApplication, JobOffer)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(JobApplication.id == application_id, JobOffer.employer_id == employer_id)
    ).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return result


def _application_for_participant(
    session: Session, application_id: str, user: User
) -> tuple[JobApplication, JobOffer]:
    result = session.execute(
        select(JobApplication, JobOffer)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(JobApplication.id == application_id)
    ).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    application, offer = result
    allowed = (
        offer.employer_id == user.id
        if user.role == Role.EMPLOYER
        else application.candidate_id == user.id
    )
    if not allowed:
        raise HTTPException(status_code=404, detail="Application not found.")
    return application, offer


def _notification(
    session: Session,
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    resource_type: str,
    resource_id: str,
) -> None:
    preference = session.get(EmployerNotificationPreference, (user_id, notification_type))
    if preference is not None and not preference.enabled:
        return
    session.add(
        EmployerNotification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )


@router.get("/employer/candidates", response_model=list[CandidateDiscoveryResponse], tags=["employer candidates"])
def search_candidates(
    q: str | None = Query(default=None, max_length=100),
    skill: str | None = Query(default=None, max_length=60),
    location: str | None = Query(default=None, max_length=120),
    offer_id: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    user: User = Depends(require_permission(Permission.CANDIDATE_DISCOVERY_READ)),
    session: Session = Depends(get_session),
) -> list[CandidateDiscoveryResponse]:
    offer = None
    if offer_id:
        offer = session.scalar(
            select(JobOffer).where(JobOffer.id == offer_id, JobOffer.employer_id == user.id)
        )
        if offer is None:
            raise HTTPException(status_code=404, detail="Job offer not found.")
    profiles = list(
        session.scalars(
            select(CandidateProfile)
            .join(User, User.id == CandidateProfile.user_id)
            .where(CandidateProfile.employer_discoverable.is_(True), User.role == Role.CANDIDATE)
            .order_by(CandidateProfile.updated_at.desc())
        )
    )
    q_key = q.strip().casefold() if q else None
    skill_key = skill.strip().casefold() if skill else None
    location_key = location.strip().casefold() if location else None
    results = []
    for profile in profiles:
        searchable = " ".join(
            [profile.professional_headline or "", *profile.skills,
             *(str(item.get("job_title", "")) for item in profile.experience_entries),
             *(str(item.get("field_of_study", "")) for item in profile.education_entries)]
        ).casefold()
        if q_key and q_key not in searchable:
            continue
        if skill_key and not any(skill_key in item.casefold() for item in profile.skills):
            continue
        if location_key and location_key not in (profile.location or "").casefold():
            continue
        matches = [item for item in (offer.required_skills if offer else []) if item.casefold() in {value.casefold() for value in profile.skills}]
        missing = [item for item in (offer.required_skills if offer else []) if item not in matches]
        results.append(
            CandidateDiscoveryResponse(
                candidate_id=profile.user_id,
                professional_headline=profile.professional_headline,
                skills=profile.skills,
                location=profile.location,
                experience_summary=profile.experience_entries[:3],
                education_summary=profile.education_entries[:3],
                matched_skills=matches,
                missing_skills=missing,
            )
        )
        record_sensitive_read(session, actor=user, resource_type="discoverable_candidate", resource_id=profile.user_id)
        if len(results) >= limit:
            break
    if results:
        session.commit()
    return results


@router.get("/employer/candidates/{candidate_id}", response_model=CandidateDiscoveryResponse, tags=["employer candidates"])
def get_discoverable_candidate(
    candidate_id: str,
    user: User = Depends(require_permission(Permission.CANDIDATE_DISCOVERY_READ)),
    session: Session = Depends(get_session),
) -> CandidateDiscoveryResponse:
    profile = session.scalar(
        select(CandidateProfile)
        .join(User, User.id == CandidateProfile.user_id)
        .where(
            CandidateProfile.user_id == candidate_id,
            CandidateProfile.employer_discoverable.is_(True),
            User.role == Role.CANDIDATE,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Candidate not found or not discoverable.")
    record_sensitive_read(session, actor=user, resource_type="discoverable_candidate", resource_id=candidate_id)
    session.commit()
    return CandidateDiscoveryResponse(
        candidate_id=profile.user_id,
        professional_headline=profile.professional_headline,
        skills=profile.skills,
        location=profile.location,
        experience_summary=profile.experience_entries,
        education_summary=profile.education_entries,
    )


@router.get("/employer/talent-pools", response_model=list[TalentPoolResponse], tags=["employer talent"])
def list_talent_pools(
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> list[TalentPoolResponse]:
    pools = list(session.scalars(select(TalentPool).where(TalentPool.employer_id == user.id).order_by(TalentPool.created_at.desc())))
    return [
        TalentPoolResponse(
            id=pool.id,
            name=pool.name,
            created_at=pool.created_at,
            candidate_count=session.scalar(select(func.count()).select_from(TalentPoolMember).where(TalentPoolMember.pool_id == pool.id)) or 0,
        )
        for pool in pools
    ]


@router.post("/employer/talent-pools", response_model=TalentPoolResponse, status_code=201, tags=["employer talent"])
def create_talent_pool(
    request: TalentPoolCreateRequest,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> TalentPoolResponse:
    pool = TalentPool(employer_id=user.id, name=request.name)
    session.add(pool)
    session.commit()
    session.refresh(pool)
    return TalentPoolResponse(id=pool.id, name=pool.name, created_at=pool.created_at, candidate_count=0)


@router.post("/employer/talent-pools/{pool_id}/members", status_code=201, tags=["employer talent"])
def add_talent_pool_member(
    pool_id: str,
    request: TalentPoolMemberRequest,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    pool = session.scalar(select(TalentPool).where(TalentPool.id == pool_id, TalentPool.employer_id == user.id))
    discoverable = session.scalar(select(CandidateProfile.user_id).where(CandidateProfile.user_id == request.candidate_id, CandidateProfile.employer_discoverable.is_(True)))
    if pool is None or discoverable is None:
        raise HTTPException(status_code=404, detail="Talent pool or discoverable candidate not found.")
    member = TalentPoolMember(pool_id=pool.id, candidate_id=request.candidate_id, private_note=request.private_note)
    session.add(member)
    session.commit()
    return {"id": member.id, "candidate_id": member.candidate_id}


@router.delete("/employer/talent-pools/{pool_id}/members/{candidate_id}", status_code=204, tags=["employer talent"])
def remove_talent_pool_member(
    pool_id: str,
    candidate_id: str,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> None:
    member = session.scalar(
        select(TalentPoolMember)
        .join(TalentPool, TalentPool.id == TalentPoolMember.pool_id)
        .where(TalentPool.id == pool_id, TalentPool.employer_id == user.id, TalentPoolMember.candidate_id == candidate_id)
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Talent pool member not found.")
    session.delete(member)
    session.commit()


@router.get("/employer/talent-pools/{pool_id}/members", response_model=list[TalentPoolMemberResponse], tags=["employer talent"])
def list_talent_pool_members(
    pool_id: str,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> list[TalentPoolMemberResponse]:
    pool = session.scalar(select(TalentPool.id).where(TalentPool.id == pool_id, TalentPool.employer_id == user.id))
    if pool is None:
        raise HTTPException(status_code=404, detail="Talent pool not found.")
    rows = session.execute(
        select(TalentPoolMember, CandidateProfile)
        .join(CandidateProfile, CandidateProfile.user_id == TalentPoolMember.candidate_id)
        .where(TalentPoolMember.pool_id == pool_id, CandidateProfile.employer_discoverable.is_(True))
        .order_by(TalentPoolMember.created_at.desc())
    )
    return [TalentPoolMemberResponse(candidate_id=member.candidate_id, professional_headline=profile.professional_headline, skills=profile.skills, location=profile.location, private_note=member.private_note, created_at=member.created_at) for member, profile in rows]


@router.get("/employer/applications/{application_id}/detail", response_model=EmployerApplicationDetailResponse, tags=["employer applications"])
def employer_application_detail(
    application_id: str,
    user: User = Depends(require_permission(Permission.APPLICANT_READ_BY_APPLICATION)),
    session: Session = Depends(get_session),
) -> EmployerApplicationDetailResponse:
    application, offer = _application_for_employer(session, application_id, user.id)
    candidate = session.get(CandidateProfile, application.candidate_id)
    record_sensitive_read(session, actor=user, resource_type="job_applicant", resource_id=application.candidate_id)
    history = session.scalars(select(JobApplicationStatusHistory).where(JobApplicationStatusHistory.application_id == application.id).order_by(JobApplicationStatusHistory.created_at))
    session.commit()
    return EmployerApplicationDetailResponse(
        id=application.id,
        job_offer_id=offer.id,
        job_title=offer.title,
        location=offer.location,
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        candidate_name=candidate.full_name if candidate else None,
        candidate_location=candidate.location if candidate else None,
        candidate_skills=candidate.skills if candidate else [],
        professional_headline=candidate.professional_headline if candidate else None,
        education_entries=candidate.education_entries if candidate else [],
        experience_entries=candidate.experience_entries if candidate else [],
        status_history=[ApplicationStatusHistoryResponse(id=row.id, from_status=row.from_status, to_status=row.to_status, created_at=row.created_at) for row in history],
    )


@router.get("/employer/applications/{application_id}/notes", response_model=list[ApplicationNoteResponse], tags=["employer applications"])
def list_application_notes(
    application_id: str,
    user: User = Depends(require_permission(Permission.APPLICANT_READ_BY_APPLICATION)),
    session: Session = Depends(get_session),
) -> list[ApplicationNoteResponse]:
    _application_for_employer(session, application_id, user.id)
    rows = session.scalars(select(ApplicationNote).where(ApplicationNote.application_id == application_id).order_by(ApplicationNote.created_at))
    return [ApplicationNoteResponse(id=row.id, content=row.content, created_at=row.created_at) for row in rows]


@router.post("/employer/applications/{application_id}/notes", response_model=ApplicationNoteResponse, status_code=201, tags=["employer applications"])
def add_application_note(
    application_id: str,
    request: ApplicationNoteCreateRequest,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> ApplicationNoteResponse:
    _application_for_employer(session, application_id, user.id)
    note = ApplicationNote(application_id=application_id, author_id=user.id, content=request.content)
    session.add(note)
    session.commit()
    session.refresh(note)
    return ApplicationNoteResponse(id=note.id, content=note.content, created_at=note.created_at)


@router.get("/employer/applications/{application_id}/evaluation", response_model=ApplicationEvaluationResponse | None, tags=["employer applications"])
def get_application_evaluation(
    application_id: str,
    user: User = Depends(require_permission(Permission.APPLICANT_READ_BY_APPLICATION)),
    session: Session = Depends(get_session),
) -> ApplicationEvaluationResponse | None:
    _application_for_employer(session, application_id, user.id)
    evaluation = session.scalar(select(ApplicationEvaluation).where(ApplicationEvaluation.application_id == application_id, ApplicationEvaluation.evaluator_id == user.id))
    if evaluation is None:
        return None
    return ApplicationEvaluationResponse(id=evaluation.id, criteria=evaluation.criteria, strengths=evaluation.strengths, concerns=evaluation.concerns, updated_at=evaluation.updated_at)


@router.put("/employer/applications/{application_id}/evaluation", response_model=ApplicationEvaluationResponse, tags=["employer applications"])
def save_application_evaluation(
    application_id: str,
    request: ApplicationEvaluationRequest,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> ApplicationEvaluationResponse:
    _application_for_employer(session, application_id, user.id)
    evaluation = session.scalar(select(ApplicationEvaluation).where(ApplicationEvaluation.application_id == application_id, ApplicationEvaluation.evaluator_id == user.id))
    if evaluation is None:
        evaluation = ApplicationEvaluation(application_id=application_id, evaluator_id=user.id, criteria=request.criteria, strengths=request.strengths, concerns=request.concerns)
        session.add(evaluation)
    else:
        evaluation.criteria = request.criteria
        evaluation.strengths = request.strengths
        evaluation.concerns = request.concerns
    session.commit()
    session.refresh(evaluation)
    return ApplicationEvaluationResponse(id=evaluation.id, criteria=evaluation.criteria, strengths=evaluation.strengths, concerns=evaluation.concerns, updated_at=evaluation.updated_at)


@router.get("/employer/conversations", response_model=list[ConversationResponse], tags=["employer messages"])
def list_employer_conversations(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ConversationResponse]:
    rows = session.execute(
        select(Conversation, JobApplication, JobOffer, CandidateProfile)
        .join(JobApplication, JobApplication.id == Conversation.application_id)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == JobApplication.candidate_id)
        .where(JobOffer.employer_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return [
        ConversationResponse(
            id=conversation.id,
            application_id=application.id,
            candidate_name=profile.full_name if profile else None,
            job_title=offer.title,
            updated_at=conversation.updated_at,
            unread_count=session.scalar(select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id, Message.sender_id != user.id, Message.read_at.is_(None))) or 0,
        )
        for conversation, application, offer, profile in rows
    ]


@router.post("/applications/{application_id}/conversation", response_model=ConversationResponse, status_code=201, tags=["messages"])
def get_or_create_conversation(
    application_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConversationResponse:
    application, offer = _application_for_participant(session, application_id, user)
    conversation = session.scalar(select(Conversation).where(Conversation.application_id == application.id))
    if conversation is None:
        conversation = Conversation(application_id=application.id)
        session.add(conversation)
        session.flush()
    candidate = session.get(CandidateProfile, application.candidate_id)
    session.commit()
    session.refresh(conversation)
    return ConversationResponse(id=conversation.id, application_id=application.id, candidate_name=candidate.full_name if candidate else None, job_title=offer.title, updated_at=conversation.updated_at, unread_count=0)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse], tags=["messages"])
def list_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MessageResponse]:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    _application_for_participant(session, conversation.application_id, user)
    rows = list(session.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)))
    now = datetime.now(timezone.utc)
    changed = False
    for row in rows:
        if row.sender_id != user.id and row.read_at is None:
            row.read_at = now
            changed = True
    if changed:
        session.commit()
    return [MessageResponse(id=row.id, sender_id=row.sender_id, content=row.content, created_at=row.created_at, read_at=row.read_at) for row in rows]


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201, tags=["messages"])
def send_message(
    conversation_id: str,
    request: MessageCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    application, offer = _application_for_participant(session, conversation.application_id, user)
    if application.status in {JobApplicationStatus.WITHDRAWN, JobApplicationStatus.REJECTED}:
        raise HTTPException(status_code=409, detail="Messaging is closed for this application.")
    recipient_id = application.candidate_id if user.id == offer.employer_id else offer.employer_id
    message = Message(conversation_id=conversation.id, sender_id=user.id, content=request.content)
    conversation.updated_at = datetime.now(timezone.utc)
    session.add(message)
    _notification(session, recipient_id, "message", "Nouveau message", "Vous avez reçu un message concernant une candidature.", "conversation", conversation.id)
    session.commit()
    session.refresh(message)
    return MessageResponse(id=message.id, sender_id=message.sender_id, content=message.content, created_at=message.created_at, read_at=message.read_at)


@router.get("/employer/interviews", response_model=list[InterviewResponse], tags=["employer interviews"])
def list_employer_interviews(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[InterviewResponse]:
    stmt = (
        select(Interview, JobApplication, JobOffer, CandidateProfile)
        .join(JobApplication, JobApplication.id == Interview.application_id)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == JobApplication.candidate_id)
        .order_by(Interview.starts_at)
    )
    stmt = stmt.where(JobOffer.employer_id == user.id) if user.role == Role.EMPLOYER else stmt.where(JobApplication.candidate_id == user.id)
    return [InterviewResponse(id=item.id, application_id=application.id, job_title=offer.title, candidate_name=profile.full_name if profile else None, starts_at=item.starts_at, duration_minutes=item.duration_minutes, format=item.format, meeting_details=item.meeting_details, status=item.status.value) for item, application, offer, profile in session.execute(stmt)]


@router.post("/employer/interviews", response_model=InterviewResponse, status_code=201, tags=["employer interviews"])
def create_interview(
    request: InterviewCreateRequest,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> InterviewResponse:
    application, offer = _application_for_employer(session, request.application_id, user.id)
    if application.status in {JobApplicationStatus.HIRED, JobApplicationStatus.REJECTED, JobApplicationStatus.WITHDRAWN}:
        raise HTTPException(status_code=409, detail="An interview cannot be scheduled for a closed application.")
    previous_status = application.status
    interview = Interview(application_id=application.id, created_by=user.id, starts_at=request.starts_at, duration_minutes=request.duration_minutes, format=request.format, meeting_details=request.meeting_details)
    session.add(interview)
    session.flush()
    for participant_id in set([user.id, *request.interviewer_ids]):
        member = session.scalar(select(OrganisationMembership.id).where(OrganisationMembership.user_id == participant_id, OrganisationMembership.organisation_id.in_(select(OrganisationMembership.organisation_id).where(OrganisationMembership.user_id == user.id))))
        if participant_id != user.id and member is None:
            session.rollback()
            raise HTTPException(status_code=422, detail="Interviewers must belong to your organisation.")
        session.add(InterviewParticipant(interview_id=interview.id, user_id=participant_id))
    candidate = session.get(CandidateProfile, application.candidate_id)
    _notification(session, application.candidate_id, "interview_proposed", "Entretien proposé", f"Un entretien est proposé pour {offer.title}.", "interview", interview.id)
    if application.status not in {JobApplicationStatus.INTERVIEW, JobApplicationStatus.INTERVIEW_COMPLETED}:
        application.status = JobApplicationStatus.INTERVIEW
        session.add(JobApplicationStatusHistory(application_id=application.id, actor_id=user.id, from_status=previous_status, to_status=JobApplicationStatus.INTERVIEW))
        record_application_status_event(session, application, previous_status, JobApplicationStatus.INTERVIEW, "employer")
    session.commit()
    session.refresh(interview)
    return InterviewResponse(id=interview.id, application_id=application.id, job_title=offer.title, candidate_name=candidate.full_name if candidate else None, starts_at=interview.starts_at, duration_minutes=interview.duration_minutes, format=interview.format, meeting_details=interview.meeting_details, status=interview.status.value)


@router.patch("/employer/interviews/{interview_id}/status", response_model=InterviewResponse, tags=["employer interviews"])
def update_interview_status(
    interview_id: str,
    request: InterviewStatusUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> InterviewResponse:
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    if user.role not in {Role.EMPLOYER, Role.CANDIDATE}:
        raise HTTPException(status_code=403, detail="Only interview participants may update interview status.")
    application, offer = _application_for_participant(session, interview.application_id, user)
    allowed = {
        InterviewStatus.PROPOSED: {InterviewStatus.CONFIRMED, InterviewStatus.CANCELLED},
        InterviewStatus.CONFIRMED: {InterviewStatus.COMPLETED, InterviewStatus.CANCELLED, InterviewStatus.NO_SHOW},
    }
    next_status = InterviewStatus(request.status)
    if user.role == Role.CANDIDATE and next_status not in {InterviewStatus.CONFIRMED, InterviewStatus.CANCELLED}:
        raise HTTPException(status_code=403, detail="Candidates can only confirm or decline proposed interviews.")
    if next_status not in allowed.get(interview.status, set()):
        raise HTTPException(status_code=409, detail="This interview status transition is not allowed.")
    interview.status = next_status
    if next_status == InterviewStatus.CONFIRMED:
        _notification(session, offer.employer_id, "interview_confirmed", "Entretien confirmé", "Le candidat a confirmé un entretien.", "interview", interview.id)
    session.commit()
    candidate = session.get(CandidateProfile, application.candidate_id)
    return InterviewResponse(id=interview.id, application_id=application.id, job_title=offer.title, candidate_name=candidate.full_name if candidate else None, starts_at=interview.starts_at, duration_minutes=interview.duration_minutes, format=interview.format, meeting_details=interview.meeting_details, status=interview.status.value)


@router.post("/employer/interviews/{interview_id}/feedback", response_model=InterviewFeedbackResponse, status_code=201, tags=["employer interviews"])
def save_interview_feedback(
    interview_id: str,
    request: InterviewFeedbackRequest,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> InterviewFeedbackResponse:
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    _application_for_employer(session, interview.application_id, user.id)
    if interview.status != InterviewStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Feedback can be added after the interview is completed.")
    feedback = session.scalar(select(InterviewFeedback).where(InterviewFeedback.interview_id == interview.id, InterviewFeedback.author_id == user.id))
    if feedback is None:
        feedback = InterviewFeedback(interview_id=interview.id, author_id=user.id, criteria=request.criteria, recommendation=request.recommendation, notes=request.notes)
        session.add(feedback)
    else:
        feedback.criteria = request.criteria
        feedback.recommendation = request.recommendation
        feedback.notes = request.notes
    session.commit()
    session.refresh(feedback)
    return InterviewFeedbackResponse(id=feedback.id, criteria=feedback.criteria, recommendation=feedback.recommendation, notes=feedback.notes, created_at=feedback.created_at)


def _decision_response(decision: JobOfferDecision, offer: JobOffer) -> JobOfferDecisionResponse:
    return JobOfferDecisionResponse(id=decision.id, application_id=decision.application_id, job_title=offer.title, status=decision.status.value, offered_at=decision.offered_at, response_deadline=decision.response_deadline, proposed_conditions=decision.proposed_conditions, responded_at=decision.responded_at)


@router.post("/employer/applications/{application_id}/offer-decision", response_model=JobOfferDecisionResponse, status_code=201, tags=["employer applications"])
def create_offer_decision(
    application_id: str,
    request: JobOfferDecisionCreateRequest,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> JobOfferDecisionResponse:
    application, offer = _application_for_employer(session, application_id, user.id)
    if application.status != JobApplicationStatus.OFFER_MADE:
        raise HTTPException(status_code=409, detail="Move the application to offer made before sending formal terms.")
    existing = session.scalar(select(JobOfferDecision).where(JobOfferDecision.application_id == application.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A formal offer already exists for this application.")
    if request.response_deadline and request.response_deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="The response deadline must be in the future.")
    decision = JobOfferDecision(application_id=application.id, response_deadline=request.response_deadline, proposed_conditions=request.proposed_conditions)
    session.add(decision)
    _notification(session, application.candidate_id, "offer_decision", "Offre d’emploi reçue", f"Vous avez reçu une offre concernant {offer.title}.", "offer_decision", decision.id)
    session.commit()
    session.refresh(decision)
    return _decision_response(decision, offer)


@router.get("/candidate/offer-decisions", response_model=list[JobOfferDecisionResponse], tags=["candidate applications"])
def candidate_offer_decisions(
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_OWN)),
    session: Session = Depends(get_session),
) -> list[JobOfferDecisionResponse]:
    rows = session.execute(select(JobOfferDecision, JobApplication, JobOffer).join(JobApplication, JobApplication.id == JobOfferDecision.application_id).join(JobOffer, JobOffer.id == JobApplication.job_offer_id).where(JobApplication.candidate_id == user.id).order_by(JobOfferDecision.offered_at.desc()))
    return [_decision_response(decision, offer) for decision, _, offer in rows]


@router.patch("/candidate/offer-decisions/{decision_id}", response_model=JobOfferDecisionResponse, tags=["candidate applications"])
def respond_to_offer_decision(
    decision_id: str,
    request: JobOfferDecisionUpdateRequest,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_OWN)),
    session: Session = Depends(get_session),
) -> JobOfferDecisionResponse:
    row = session.execute(select(JobOfferDecision, JobApplication, JobOffer).join(JobApplication, JobApplication.id == JobOfferDecision.application_id).join(JobOffer, JobOffer.id == JobApplication.job_offer_id).where(JobOfferDecision.id == decision_id, JobApplication.candidate_id == user.id).with_for_update()).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Offer decision not found.")
    decision, application, offer = row
    if decision.status != JobOfferDecisionStatus.PENDING:
        raise HTTPException(status_code=409, detail="This offer decision already has a response.")
    now = datetime.now(timezone.utc)
    if decision.response_deadline and decision.response_deadline <= now:
        decision.status = JobOfferDecisionStatus.EXPIRED
        session.commit()
        raise HTTPException(status_code=409, detail="The response deadline has passed.")
    decision.status = JobOfferDecisionStatus(request.status)
    decision.responded_at = now
    if decision.status == JobOfferDecisionStatus.ACCEPTED:
        previous_status = application.status
        application.status = JobApplicationStatus.HIRED
        session.add(JobApplicationStatusHistory(application_id=application.id, actor_id=user.id, from_status=previous_status, to_status=application.status))
        record_application_status_event(session, application, previous_status, JobApplicationStatus.HIRED, "employer")
    _notification(session, offer.employer_id, "offer_decision_response", "Réponse à une offre", "Le candidat a répondu à l’offre d’emploi.", "offer_decision", decision.id)
    session.commit()
    return _decision_response(decision, offer)


@router.get("/employer/notifications", response_model=list[NotificationResponse], tags=["employer notifications"])
def list_notifications(
    unread_only: bool = False,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> list[NotificationResponse]:
    stmt = select(EmployerNotification).where(EmployerNotification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(EmployerNotification.read_at.is_(None))
    rows = session.scalars(stmt.order_by(EmployerNotification.created_at.desc()).limit(100))
    return [NotificationResponse(id=item.id, notification_type=item.notification_type, title=item.title, body=item.body, resource_type=item.resource_type, resource_id=item.resource_id, read_at=item.read_at, created_at=item.created_at) for item in rows]


@router.patch("/employer/notifications/{notification_id}/read", response_model=NotificationResponse, tags=["employer notifications"])
def mark_notification_read(
    notification_id: str,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> NotificationResponse:
    item = session.scalar(select(EmployerNotification).where(EmployerNotification.id == notification_id, EmployerNotification.user_id == user.id))
    if item is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    item.read_at = item.read_at or datetime.now(timezone.utc)
    session.commit()
    return NotificationResponse(id=item.id, notification_type=item.notification_type, title=item.title, body=item.body, resource_type=item.resource_type, resource_id=item.resource_id, read_at=item.read_at, created_at=item.created_at)


_NOTIFICATION_TYPES = ("application", "message", "interview_proposed", "interview_confirmed", "status_change")


@router.get("/employer/notification-preferences", response_model=list[NotificationPreferenceResponse], tags=["employer notifications"])
def get_notification_preferences(
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> list[NotificationPreferenceResponse]:
    saved = {
        item.notification_type: item.enabled
        for item in session.scalars(
            select(EmployerNotificationPreference).where(EmployerNotificationPreference.user_id == user.id)
        )
    }
    return [NotificationPreferenceResponse(notification_type=name, enabled=saved.get(name, True)) for name in _NOTIFICATION_TYPES]


@router.put("/employer/notification-preferences/{notification_type}", response_model=NotificationPreferenceResponse, tags=["employer notifications"])
def update_notification_preference(
    notification_type: str,
    request: NotificationPreferenceUpdate,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> NotificationPreferenceResponse:
    if notification_type not in _NOTIFICATION_TYPES:
        raise HTTPException(status_code=404, detail="Notification preference not found.")
    preference = session.get(EmployerNotificationPreference, (user.id, notification_type))
    if preference is None:
        preference = EmployerNotificationPreference(user_id=user.id, notification_type=notification_type, enabled=request.enabled)
        session.add(preference)
    else:
        preference.enabled = request.enabled
    session.commit()
    return NotificationPreferenceResponse(notification_type=notification_type, enabled=preference.enabled)


def _employer_organisation(session: Session, user_id: str) -> Organisation:
    organisation = session.scalar(
        select(Organisation)
        .join(OrganisationMembership, OrganisationMembership.organisation_id == Organisation.id)
        .where(OrganisationMembership.user_id == user_id, Organisation.organisation_type == OrganisationType.EMPLOYER)
    )
    if organisation is None:
        raise HTTPException(status_code=404, detail="No employer organisation is linked to this account.")
    return organisation


@router.post("/employer/organisation/verification", response_model=OrganisationVerificationResponse, status_code=201, tags=["employer organisation"])
def submit_organisation_verification(
    request: OrganisationVerificationCreateRequest,
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> OrganisationVerificationResponse:
    organisation = _employer_organisation(session, user.id)
    if organisation.verification_status == OrganisationVerificationStatus.VERIFIED:
        raise HTTPException(status_code=409, detail="This organisation is already verified.")
    pending = session.scalar(select(OrganisationVerificationRequest).where(OrganisationVerificationRequest.organisation_id == organisation.id, OrganisationVerificationRequest.status == OrganisationVerificationStatus.PENDING))
    if pending is not None:
        raise HTTPException(status_code=409, detail="A verification request is already pending.")
    verification = OrganisationVerificationRequest(organisation_id=organisation.id, submitted_by=user.id, supporting_information=request.supporting_information, evidence_url=request.evidence_url)
    organisation.verification_status = OrganisationVerificationStatus.PENDING
    session.add(verification)
    session.commit()
    session.refresh(verification)
    return OrganisationVerificationResponse(id=verification.id, organisation_id=organisation.id, organisation_name=organisation.name, status=verification.status.value, supporting_information=verification.supporting_information, evidence_url=verification.evidence_url, reviewer_note=verification.reviewer_note, created_at=verification.created_at)


@router.get("/employer/organisation/verification", response_model=OrganisationVerificationResponse | None, tags=["employer organisation"])
def get_organisation_verification(
    user: User = Depends(require_permission(Permission.OFFER_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> OrganisationVerificationResponse | None:
    organisation = _employer_organisation(session, user.id)
    verification = session.scalar(select(OrganisationVerificationRequest).where(OrganisationVerificationRequest.organisation_id == organisation.id).order_by(OrganisationVerificationRequest.created_at.desc()))
    if verification is None:
        return None
    return OrganisationVerificationResponse(id=verification.id, organisation_id=organisation.id, organisation_name=organisation.name, status=verification.status.value, supporting_information=verification.supporting_information, evidence_url=verification.evidence_url, reviewer_note=verification.reviewer_note, created_at=verification.created_at)


@router.get("/admin/organisations/verification", response_model=list[OrganisationVerificationResponse], tags=["administration"])
def pending_organisation_verifications(
    user: User = Depends(require_permission(Permission.ORGANISATION_VERIFICATION_REVIEW)),
    session: Session = Depends(get_session),
) -> list[OrganisationVerificationResponse]:
    rows = session.execute(select(OrganisationVerificationRequest, Organisation).join(Organisation, Organisation.id == OrganisationVerificationRequest.organisation_id).where(OrganisationVerificationRequest.status == OrganisationVerificationStatus.PENDING).order_by(OrganisationVerificationRequest.created_at)).all()
    return [OrganisationVerificationResponse(id=request.id, organisation_id=organisation.id, organisation_name=organisation.name, status=request.status.value, supporting_information=request.supporting_information, evidence_url=request.evidence_url, reviewer_note=request.reviewer_note, created_at=request.created_at) for request, organisation in rows]


@router.patch("/admin/organisations/verification/{verification_id}", response_model=OrganisationVerificationResponse, tags=["administration"])
def review_organisation_verification(
    verification_id: str,
    request: OrganisationVerificationReviewRequest,
    user: User = Depends(require_permission(Permission.ORGANISATION_VERIFICATION_REVIEW)),
    session: Session = Depends(get_session),
) -> OrganisationVerificationResponse:
    verification = session.get(OrganisationVerificationRequest, verification_id)
    if verification is None or verification.status != OrganisationVerificationStatus.PENDING:
        raise HTTPException(status_code=404, detail="Pending verification request not found.")
    next_status = OrganisationVerificationStatus(request.status)
    verification.status = next_status
    verification.reviewer_note = request.reviewer_note.strip()
    organisation = session.get(Organisation, verification.organisation_id)
    if organisation is not None:
        organisation.verification_status = next_status
    record_audit_event(session, action="admin.organisation_verification.reviewed", actor=user, resource_type="organisation_verification", resource_id=verification.id, details={"status": next_status.value})
    session.commit()
    session.refresh(verification)
    return OrganisationVerificationResponse(id=verification.id, organisation_id=organisation.id if organisation else None, organisation_name=organisation.name if organisation else None, status=verification.status.value, supporting_information=verification.supporting_information, evidence_url=verification.evidence_url, reviewer_note=verification.reviewer_note, created_at=verification.created_at)


@router.get("/employer/analytics", response_model=EmployerAnalyticsResponse, tags=["employer analytics"])
def employer_analytics(
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> EmployerAnalyticsResponse:
    offers = list(session.scalars(select(JobOffer).where(JobOffer.employer_id == user.id)))
    rows = list(session.execute(select(JobApplication, JobOffer).join(JobOffer, JobOffer.id == JobApplication.job_offer_id).where(JobOffer.employer_id == user.id)))
    counts = {item.value: 0 for item in JobApplicationStatus}
    per_offer = {offer.id: {"job_offer_id": offer.id, "title": offer.title, "applications": 0} for offer in offers}
    app_ids = []
    for application, offer in rows:
        counts[application.status.value] += 1
        per_offer[offer.id]["applications"] += 1
        app_ids.append(application.id)
    history_rows = list(session.scalars(select(JobApplicationStatusHistory).where(JobApplicationStatusHistory.application_id.in_(app_ids)))) if app_ids else []
    review_durations: list[float] = []
    history_by_application: dict[str, list[JobApplicationStatusHistory]] = {}
    for item in history_rows:
        history_by_application.setdefault(item.application_id, []).append(item)
    for application, _ in rows:
        entries = sorted(history_by_application.get(application.id, []), key=lambda item: item.created_at)
        first_review = next((item for item in entries if item.to_status != JobApplicationStatus.SUBMITTED), None)
        if first_review is not None:
            review_durations.append(max(0, (first_review.created_at - application.created_at).total_seconds() / 3600))
    interviewed_statuses = {
        JobApplicationStatus.INTERVIEW,
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.OFFER_MADE,
        JobApplicationStatus.HIRED,
    }
    interviews = len({item.application_id for item in history_rows if item.to_status in interviewed_statuses})
    hires = counts[JobApplicationStatus.HIRED.value]
    return EmployerAnalyticsResponse(
        total_applications=len(rows),
        applications_by_status=counts,
        applications_per_offer=list(per_offer.values()),
        shortlisted=counts[JobApplicationStatus.SHORTLISTED.value],
        interviews=interviews,
        hires_reported=hires,
        rejected=counts[JobApplicationStatus.REJECTED.value],
        withdrawn=counts[JobApplicationStatus.WITHDRAWN.value],
        application_to_interview_percent=round(interviews * 100 / len(rows)) if rows else None,
        interview_to_hire_percent=round(hires * 100 / interviews) if interviews else None,
        average_time_to_first_review_hours=round(sum(review_durations) / len(review_durations), 1) if review_durations else None,
        has_sufficient_data=len(rows) >= 5,
    )
