import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from mahara_data.db.models.candidates import CandidatePII
from mahara_data.db.models.candidates import Candidate
from mahara_data.db.models.employers import Application, Employer, JobOffer, JobOfferSkill
from mahara_data.db.models.matching import MatchResult
from mahara_data.db.models.platform import AuditLog, NotificationOutbox
from mahara_data.db.models.reference import Governorate, Sector
from mahara_data.db.models.taxonomy import Occupation, Skill
from mahara_data.enums import ApplicationStatus, HiringDecision, OfferStatus
from mahara_data.schemas.common import Page
from mahara_data.schemas.offer import NormalizedJobOffer
from .config import get_settings

from .services.applications import (
    ApplicationWorkflowError,
    create_candidate_application,
    list_candidate_applications as get_candidate_applications,
    list_employer_applications as get_employer_applications,
    list_employer_applications_page as get_employer_applications_page,
    get_employer_application_detail,
    record_employer_decision as save_employer_decision,
)


class ApplicationApplyRequest(BaseModel):
    job_offer_id: uuid.UUID
    cover_note: str | None = Field(default=None, max_length=2000)
    employer_contact_consent: bool = False


class EmployerDecision(BaseModel):
    decision: HiringDecision
    reason_code: str | None = Field(default=None, max_length=64)
    match_quality: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class EmployerOfferStatusUpdate(BaseModel):
    status: str = Field(pattern="^(published|closed)$")
    expires_at: datetime | None = None


class InterviewInvitationRequest(BaseModel):
    meeting_at_local: datetime
    timezone: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("meeting_at_local")
    @classmethod
    def local_datetime_must_be_naive(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            raise ValueError("meeting_at_local must not include an offset; send timezone separately")
        return value


class ContactConsentUpdate(BaseModel):
    allow_contact: bool


def create_application_router(get_db: Any, get_current_user: Any, get_current_employer: Any) -> APIRouter:
    router = APIRouter(tags=["applications"])

    @router.patch("/api/v1/me/applications/{application_id}/contact-consent")
    def update_candidate_contact_consent(application_id: uuid.UUID, payload: ContactConsentUpdate,
                                         db: Annotated[Session, Depends(get_db)],
                                         user: Annotated[Any, Depends(get_current_user)]):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        application = db.query(Application).filter(Application.id == application_id,
            Application.candidate_id == (candidate.id if candidate else None)).with_for_update().first()
        if application is None:
            raise HTTPException(status_code=404, detail="Application not found")
        application.employer_contact_consent_at = datetime.now(timezone.utc) if payload.allow_contact else None
        if not payload.allow_contact:
            db.query(NotificationOutbox).filter(
                NotificationOutbox.application_id == application.id,
                NotificationOutbox.status.in_(("queued", "failed")),
            ).update({NotificationOutbox.status: "cancelled"}, synchronize_session=False)
        db.add(AuditLog(actor_user_id=user.id, action="candidate.employer_contact_consent_changed",
            entity_type="application", entity_id=str(application.id),
            payload={"allow_contact": payload.allow_contact}))
        db.commit()
        return {"application_id": str(application.id), "employer_contact_consent": payload.allow_contact}

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
                employer_contact_consent=payload.employer_contact_consent,
            )
        except ApplicationWorkflowError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    @router.get("/api/v1/employer/applications")
    def list_employer_applications(
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        return get_employer_applications(db, employer=employer)

    @router.get("/api/v1/employer/applications/page")
    def list_employer_applications_page(
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 25,
        status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
        job_offer_id: uuid.UUID | None = None,
        min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    ):
        items, total = get_employer_applications_page(
            db,
            employer=employer,
            page=page,
            page_size=page_size,
            status=status_filter,
            job_offer_id=job_offer_id,
            min_score=min_score,
        )
        return Page[dict](items=items, total=total, page=page, page_size=page_size)

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
                "archived_at": offer.archived_at.isoformat() if offer.archived_at else None,
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

    @router.get("/api/v1/employer/offers/page")
    def list_employer_offers_page(
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 25,
        status_filter: OfferStatus | None = Query(default=None, alias="status"),
        include_archived: bool = False,
    ):
        base = db.query(JobOffer).filter(JobOffer.employer_id == employer.id)
        if not include_archived:
            base = base.filter(JobOffer.archived_at.is_(None))
        if status_filter is not None:
            base = base.filter(JobOffer.status == status_filter)
        total = base.count()
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
        )
        if status_filter is not None:
            rows = rows.filter(JobOffer.status == status_filter)
        if not include_archived:
            rows = rows.filter(JobOffer.archived_at.is_(None))
        result = rows.order_by(JobOffer.published_at.desc().nullslast(), JobOffer.created_at.desc()).limit(page_size).offset((page - 1) * page_size).all()
        items = [
            {
                "job_offer_id": str(offer.id), "title": offer.title, "status": offer.status.value,
                "archived_at": offer.archived_at.isoformat() if offer.archived_at else None,
                "published_at": offer.published_at.isoformat() if offer.published_at else None,
                "expires_at": offer.expires_at.isoformat() if offer.expires_at else None,
                "applications_count": applications or 0, "submitted_count": submitted or 0,
                "shortlisted_count": shortlisted or 0, "hired_count": hired or 0,
                "rejected_count": rejected or 0,
                "top_match_score": float(top_score) if top_score is not None else None,
            }
            for offer, applications, submitted, shortlisted, hired, rejected, top_score in result
        ]
        status_counts = {
            item.value: db.query(func.count(JobOffer.id)).filter(
                JobOffer.employer_id == employer.id, JobOffer.status == item, JobOffer.archived_at.is_(None)
            ).scalar() or 0
            for item in OfferStatus
        }
        return {**Page[dict](items=items, total=total, page=page, page_size=page_size).model_dump(), "status_counts": status_counts}

    def offer_editor_payload(db: Session, offer: JobOffer) -> dict:
        occupation = db.get(Occupation, offer.occupation_id) if offer.occupation_id else None
        sector = db.get(Sector, offer.sector_id) if offer.sector_id else None
        skills = (db.query(JobOfferSkill, Skill).join(Skill, Skill.id == JobOfferSkill.skill_id)
                  .filter(JobOfferSkill.job_offer_id == offer.id).order_by(Skill.code).all())
        return NormalizedJobOffer(
            offer_id=offer.id, employer_id=offer.employer_id, title=offer.title,
            description=offer.description_raw, occupation_code=occupation.code if occupation else None,
            sector_code=sector.code if sector else None, contract_type=offer.contract_type,
            work_mode=offer.work_mode, location={"governorate_code": offer.governorate_code, "delegation": offer.delegation},
            positions_count=offer.positions_count, min_years_experience=float(offer.min_years_experience),
            education_level_min=offer.education_level_min,
            salary=(None if offer.salary_min_tnd is None and offer.salary_max_tnd is None else {
                "min_tnd": float(offer.salary_min_tnd) if offer.salary_min_tnd is not None else None,
                "max_tnd": float(offer.salary_max_tnd) if offer.salary_max_tnd is not None else None,
            }),
            skills=[{"skill_code": skill.code, "requirement": link.requirement, "min_level": link.min_level}
                    for link, skill in skills],
            languages_required=offer.languages_required, status=offer.status, source=offer.source,
            published_at=offer.published_at, expires_at=offer.expires_at,
        ).model_dump(mode="json")

    @router.get("/api/v1/employer/offers/{offer_id}/edit")
    def read_employer_offer_for_edit(offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)],
                                     employer: Annotated[Employer, Depends(get_current_employer)]):
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.employer_id == employer.id,
                                          JobOffer.archived_at.is_(None)).first()
        if offer is None:
            raise HTTPException(status_code=404, detail="Offer not found")
        return offer_editor_payload(db, offer)

    @router.put("/api/v1/employer/offers/{offer_id}")
    def edit_employer_offer(offer_id: uuid.UUID, payload: NormalizedJobOffer,
                            db: Annotated[Session, Depends(get_db)],
                            employer: Annotated[Employer, Depends(get_current_employer)]):
        from .features.employer.workflow import persist_published_offer

        offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.employer_id == employer.id).with_for_update().first()
        if offer is None or offer.archived_at is not None:
            raise HTTPException(status_code=404, detail="Offer not found")
        if offer.status is not OfferStatus.PUBLISHED:
            raise HTTPException(status_code=409, detail="Only published offers can be edited; reopen the offer first")
        data = payload.model_dump()
        data.update({"offer_id": offer.id, "employer_id": employer.id, "status": OfferStatus.PUBLISHED,
                     "published_at": offer.published_at, "source": offer.source})
        try:
            normalized = NormalizedJobOffer.model_validate(data)
            persist_published_offer(db, normalized, employer.id)
        except ValueError as error:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(error)) from error
        db.add(AuditLog(actor_user_id=employer.user_id,
            actor_service=None if employer.user_id else "employer-workspace", action="employer.offer_edited",
            entity_type="job_offer", entity_id=str(offer.id), payload={"employer_id": str(employer.id)}))
        db.commit()
        db.refresh(offer)
        return offer_editor_payload(db, offer)

    @router.post("/api/v1/employer/offers/{offer_id}/archive")
    def archive_employer_offer(offer_id: uuid.UUID, db: Annotated[Session, Depends(get_db)],
                               employer: Annotated[Employer, Depends(get_current_employer)]):
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.employer_id == employer.id).with_for_update().first()
        if offer is None:
            raise HTTPException(status_code=404, detail="Offer not found")
        if offer.archived_at is not None:
            raise HTTPException(status_code=409, detail="Offer is already archived")
        if offer.status is not OfferStatus.CLOSED:
            raise HTTPException(status_code=409, detail="Close the offer before archiving it")
        pending = db.query(func.count(Application.id)).filter(
            Application.job_offer_id == offer.id,
            Application.status.in_((ApplicationStatus.SUBMITTED, ApplicationStatus.VIEWED,
                                    ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW,
                                    ApplicationStatus.OFFER_MADE)),
        ).scalar() or 0
        if pending:
            raise HTTPException(status_code=409, detail="Resolve submitted and shortlisted applications before archiving")
        offer.archived_at = datetime.now(timezone.utc)
        db.add(AuditLog(actor_user_id=employer.user_id,
            actor_service=None if employer.user_id else "employer-workspace", action="employer.offer_archived",
            entity_type="job_offer", entity_id=str(offer.id), payload={"employer_id": str(employer.id)}))
        db.commit()
        return {"job_offer_id": str(offer.id), "status": "archived", "archived_at": offer.archived_at.isoformat()}

    @router.patch("/api/v1/employer/offers/{offer_id}/status")
    def update_employer_offer_status(
        offer_id: uuid.UUID,
        payload: EmployerOfferStatusUpdate,
        db: Annotated[Session, Depends(get_db)],
        employer: Annotated[Employer, Depends(get_current_employer)],
    ):
        offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.employer_id == employer.id).with_for_update().first()
        if offer is None:
            raise HTTPException(status_code=404, detail="Offer not found")
        if offer.archived_at is not None:
            raise HTTPException(status_code=409, detail="Archived offers cannot be reopened")
        target = OfferStatus(payload.status)
        allowed = {
            OfferStatus.PUBLISHED: {OfferStatus.CLOSED},
            OfferStatus.CLOSED: {OfferStatus.PUBLISHED},
        }
        if target not in allowed.get(offer.status, set()):
            raise HTTPException(status_code=409, detail=f"Cannot change offer status from {offer.status.value} to {target.value}")
        previous = offer.status
        now = datetime.now(timezone.utc)
        if "expires_at" in payload.model_fields_set:
            if payload.expires_at is not None and (payload.expires_at.tzinfo is None or payload.expires_at <= now):
                raise HTTPException(status_code=422, detail="expires_at must be a future timezone-aware timestamp")
            offer.expires_at = payload.expires_at
        current_expiry = offer.expires_at
        if current_expiry is not None and current_expiry.tzinfo is None:
            current_expiry = current_expiry.replace(tzinfo=timezone.utc)
        if target is OfferStatus.PUBLISHED and current_expiry is not None and current_expiry <= now:
            raise HTTPException(status_code=409, detail="The offer is expired; provide a future expires_at to reopen it")
        offer.status = target
        db.add(AuditLog(
            actor_user_id=employer.user_id,
            actor_service=None if employer.user_id else "employer-workspace",
            action="employer.offer_status_changed",
            entity_type="job_offer",
            entity_id=str(offer.id),
            payload={"from": previous.value, "to": target.value, "employer_id": str(employer.id)},
        ))
        db.commit()
        db.refresh(offer)
        return {"job_offer_id": str(offer.id), "status": offer.status.value, "updated_at": offer.updated_at.isoformat()}

    @router.post("/api/v1/employer/applications/{application_id}/interviews", status_code=202)
    def invite_candidate_to_interview(application_id: uuid.UUID, payload: InterviewInvitationRequest,
                                      db: Annotated[Session, Depends(get_db)],
                                      employer: Annotated[Employer, Depends(get_current_employer)]):
        settings = get_settings()
        if not all((settings.smtp_host, settings.smtp_from_email)):
            raise HTTPException(status_code=503, detail="Interview notification delivery is not configured")
        application = (db.query(Application).join(JobOffer, JobOffer.id == Application.job_offer_id)
                       .filter(Application.id == application_id, JobOffer.employer_id == employer.id)
                       .with_for_update().first())
        if application is None:
            raise HTTPException(status_code=404, detail="Application not found")
        if application.status is not ApplicationStatus.SHORTLISTED:
            raise HTTPException(status_code=409, detail="Shortlist the candidate before sending an interview invitation")
        if application.employer_contact_consent_at is None:
            raise HTTPException(status_code=409, detail="The candidate has not consented to employer contact")
        candidate_pii = db.get(CandidatePII, application.candidate_id)
        if candidate_pii is None or not candidate_pii.email:
            raise HTTPException(status_code=409, detail="The candidate has no email address on file")
        try:
            zone = ZoneInfo(payload.timezone)
        except ZoneInfoNotFoundError as error:
            raise HTTPException(status_code=422, detail="Unknown IANA timezone") from error
        localized = payload.meeting_at_local.replace(tzinfo=zone)
        meeting_at = localized.astimezone(timezone.utc)
        if localized.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != payload.meeting_at_local:
            raise HTTPException(status_code=422, detail="The selected local time does not exist in this timezone")
        if meeting_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=422, detail="Interview time must be in the future")
        offer = db.get(JobOffer, application.job_offer_id)
        subject = f"Interview invitation: {offer.title if offer else 'job application'}"
        meeting_label = localized.strftime("%A, %d %B %Y at %H:%M %Z")
        body = (f"Hello {candidate_pii.full_name or 'candidate'},\n\n"
                f"{employer.company_name} invites you to an interview for {offer.title if offer else 'your application'}.\n"
                f"Time: {meeting_label}\n"
                f"{('Details: ' + payload.note.strip() + chr(10)) if payload.note and payload.note.strip() else ''}\n"
                "If this time does not work for you, please reply to this message.")
        notification = NotificationOutbox(
            application_id=application.id, candidate_id=application.candidate_id, employer_id=employer.id,
            meeting_at=meeting_at, meeting_timezone=payload.timezone, recipient_email=candidate_pii.email,
            subject=subject[:200], body=body, status="queued", next_attempt_at=datetime.now(timezone.utc),
        )
        duplicate = db.query(NotificationOutbox).filter(
            NotificationOutbox.application_id == application.id,
            NotificationOutbox.meeting_at == meeting_at,
            NotificationOutbox.status.in_(("queued", "sending", "sent", "failed")),
        ).first()
        if duplicate is not None:
            db.rollback()
            return {"notification_id": str(duplicate.id), "status": duplicate.status,
                    "meeting_at": duplicate.meeting_at.isoformat(), "meeting_timezone": duplicate.meeting_timezone}
        db.add(notification)
        db.add(AuditLog(actor_user_id=employer.user_id,
            actor_service=None if employer.user_id else "employer-workspace", action="employer.interview_invitation_queued",
            entity_type="application", entity_id=str(application.id),
            payload={"notification_id": str(notification.id), "meeting_at": meeting_at.isoformat(), "timezone": payload.timezone}))
        db.commit()
        db.refresh(notification)
        return {"notification_id": str(notification.id), "status": notification.status,
                "meeting_at": notification.meeting_at.isoformat(), "meeting_timezone": notification.meeting_timezone}

    @router.get("/api/v1/employer/applications/{application_id}/interviews")
    def list_interview_invitations(application_id: uuid.UUID, db: Annotated[Session, Depends(get_db)],
                                   employer: Annotated[Employer, Depends(get_current_employer)]):
        owns_application = db.query(Application.id).join(JobOffer, JobOffer.id == Application.job_offer_id).filter(
            Application.id == application_id, JobOffer.employer_id == employer.id
        ).scalar()
        if owns_application is None:
            raise HTTPException(status_code=404, detail="Application not found")
        rows = db.query(NotificationOutbox).filter(NotificationOutbox.application_id == application_id).order_by(
            NotificationOutbox.created_at.desc()).all()
        return [{"notification_id": str(item.id), "status": item.status, "meeting_at": item.meeting_at.isoformat(),
                 "meeting_timezone": item.meeting_timezone, "attempts": item.attempts,
                 "sent_at": item.sent_at.isoformat() if item.sent_at else None} for item in rows]

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
