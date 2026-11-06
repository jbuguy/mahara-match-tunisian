"""Employer dashboard aggregates, invitation listing, offer counts, and editor catalogs."""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from mahara_data.db.models.accounts import User
from mahara_data.db.models.candidates import Candidate, CandidatePII
from mahara_data.db.models.employers import Application, Employer, JobOffer
from mahara_data.db.models.matching import MatchResult
from mahara_data.db.models.platform import NotificationOutbox
from mahara_data.db.models.taxonomy import Occupation
from mahara_data.enums import ApplicationStatus, OfferStatus
from mahara_data.repositories.taxonomy import search_skills

from ...config import get_settings
from ...models import EmployerDraftSession
from ...repositories.applications import audit_candidate_identity_reads


DeliveryStatus = Literal["queued", "sending", "sent", "failed", "cancelled"]
Severity = Literal["high", "medium", "low"]

SUPPORTED_LANGUAGES = (
    {"code": "ar-TN", "label": "Arabic (Tunisia)"},
    {"code": "ar", "label": "Arabic"},
    {"code": "fr", "label": "French"},
    {"code": "en", "label": "English"},
)
LANGUAGE_LEVELS = (
    {"level": 1, "label": "Beginner"},
    {"level": 2, "label": "Intermediate"},
    {"level": 3, "label": "Advanced"},
    {"level": 4, "label": "Expert"},
)


class DashboardKpis(BaseModel):
    active_offers: int
    applications_total: int
    shortlisted: int
    hired: int
    average_match_score: float | None
    next_interview_at: str | None


class AttentionItem(BaseModel):
    type: str
    count: int
    severity: Severity
    target_route_hint: str
    sample_ids: list[str]


class DashboardTopCandidate(BaseModel):
    application_id: str
    candidate_name: str | None
    offer_title: str
    score_global: float
    status: str


class DashboardOfferSnapshot(BaseModel):
    offer_id: str
    title: str
    applications_count: int
    top_match_score: float | None
    expires_at: str | None


class BenchmarkableOffer(BaseModel):
    offer_id: str
    occupation_code: str
    governorate_code: str


class EmployerDashboard(BaseModel):
    kpis: DashboardKpis
    attention: list[AttentionItem]
    top_candidates: list[DashboardTopCandidate]
    offers_snapshot: list[DashboardOfferSnapshot]
    latest_benchmarkable_offer: BenchmarkableOffer | None


class InterviewInvitation(BaseModel):
    invitation_id: str
    application_id: str
    candidate_name: str | None
    offer_title: str
    meeting_at: str
    timezone: str
    status: DeliveryStatus


class SkillCatalogItem(BaseModel):
    skill_code: str
    label: str


class LanguageCatalog(BaseModel):
    languages: list[dict[str, str]]
    levels: list[dict[str, int | str]]


class EmployerOfferCounts(BaseModel):
    all: int
    published: int
    drafts: int
    archived: int


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sample_ids(query, limit: int = 5) -> list[str]:
    return [str(row[0]) for row in query.limit(limit).all()]


def create_employer_dashboard_router(
    get_db: Any,
    get_current_employer: Any,
) -> APIRouter:
    router = APIRouter(tags=["employer"])

    @router.get("/api/v1/employer/dashboard", response_model=EmployerDashboard)
    def employer_dashboard(
        db: Session = Depends(get_db),
        employer: Employer = Depends(get_current_employer),
    ) -> EmployerDashboard:
        now = datetime.now(timezone.utc)
        soon = now + timedelta(days=7)
        owned_offers = JobOffer.employer_id == employer.id
        owned_applications = (
            db.query(Application)
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .filter(owned_offers, Candidate.deleted_at.is_(None))
        )

        published_offers = db.query(JobOffer).filter(
            owned_offers,
            JobOffer.status == OfferStatus.PUBLISHED,
            JobOffer.archived_at.is_(None),
        )
        active_offers = published_offers.filter(
            or_(JobOffer.expires_at.is_(None), JobOffer.expires_at > now)
        ).count()

        application_totals = (
            db.query(
                func.count(Application.id),
                func.sum(case((Application.status == ApplicationStatus.SHORTLISTED, 1), else_=0)),
                func.sum(case((Application.status == ApplicationStatus.HIRED, 1), else_=0)),
            )
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .filter(owned_offers, Candidate.deleted_at.is_(None))
            .one()
        )
        scored_average = (
            db.query(func.avg(MatchResult.score_global))
            .join(Application, Application.match_result_id == MatchResult.id)
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .filter(owned_offers, Candidate.deleted_at.is_(None))
            .scalar()
        )
        next_interview = (
            db.query(func.min(NotificationOutbox.meeting_at))
            .filter(
                NotificationOutbox.employer_id == employer.id,
                NotificationOutbox.status == "sent",
                NotificationOutbox.sent_at.is_not(None),
                NotificationOutbox.meeting_at >= now,
            )
            .scalar()
        )

        new_applications = owned_applications.filter(Application.status == ApplicationStatus.SUBMITTED)
        new_count = new_applications.count()
        new_ids = _sample_ids(new_applications.order_by(Application.applied_at.desc()).with_entities(Application.id))

        active_invitation_ids = (
            db.query(NotificationOutbox.application_id)
            .filter(
                NotificationOutbox.employer_id == employer.id,
                NotificationOutbox.status.in_(("queued", "sending", "sent")),
            )
        )
        uninvited_shortlist = owned_applications.filter(
            Application.status == ApplicationStatus.SHORTLISTED,
            ~Application.id.in_(active_invitation_ids),
        )
        uninvited_count = uninvited_shortlist.count()
        uninvited_ids = _sample_ids(
            uninvited_shortlist.order_by(Application.updated_at.desc()).with_entities(Application.id)
        )

        expiring_offers = published_offers.filter(JobOffer.expires_at > now, JobOffer.expires_at <= soon)
        expiring_count = expiring_offers.count()
        expiring_ids = _sample_ids(
            expiring_offers.order_by(JobOffer.expires_at.asc()).with_entities(JobOffer.id)
        )

        draft_status = EmployerDraftSession.draft["status"].as_string()
        unfinished_drafts = db.query(EmployerDraftSession).filter(
            EmployerDraftSession.employer_id == employer.id,
            or_(
                EmployerDraftSession.draft.is_(None),
                draft_status.is_(None),
                draft_status != "published",
            ),
        )
        drafts_count = unfinished_drafts.count()
        draft_ids = _sample_ids(
            unfinished_drafts.order_by(EmployerDraftSession.updated_at.desc()).with_entities(EmployerDraftSession.id)
        )

        profile = db.get(Employer, employer.id)
        user = db.get(User, profile.user_id) if profile is not None and profile.user_id else None
        email_verified = bool(user and user.email_verified) or not get_settings().email_verification_required
        missing_profile_fields: list[str] = []
        if not email_verified:
            missing_profile_fields.append("email_verified")
        if profile is None or not profile.verified:
            missing_profile_fields.append("company_verified")
        for field in ("tax_id", "governorate_code", "website"):
            if profile is None or not getattr(profile, field):
                missing_profile_fields.append(field)

        attention: list[AttentionItem] = []
        if new_count:
            attention.append(AttentionItem(
                type="new_applications", count=new_count, severity="high",
                target_route_hint="/employer/applicants?status=submitted", sample_ids=new_ids,
            ))
        if uninvited_count:
            attention.append(AttentionItem(
                type="shortlisted_without_interview", count=uninvited_count, severity="high",
                target_route_hint="/employer/interviews", sample_ids=uninvited_ids,
            ))
        if expiring_count:
            attention.append(AttentionItem(
                type="offers_expiring", count=expiring_count, severity="medium",
                target_route_hint="/employer/offers", sample_ids=expiring_ids,
            ))
        if drafts_count:
            attention.append(AttentionItem(
                type="unfinished_drafts", count=drafts_count, severity="low",
                target_route_hint="/employer/offers/drafts", sample_ids=draft_ids,
            ))
        if missing_profile_fields:
            attention.append(AttentionItem(
                type="profile_readiness",
                count=len(missing_profile_fields),
                severity="high" if {"email_verified", "company_verified"} & set(missing_profile_fields) else "medium",
                target_route_hint="/employer/profile",
                sample_ids=missing_profile_fields,
            ))

        top_candidate_rows = (
            db.query(Application, JobOffer, Candidate, CandidatePII, MatchResult)
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .outerjoin(CandidatePII, CandidatePII.candidate_id == Candidate.id)
            .join(MatchResult, MatchResult.id == Application.match_result_id)
            .filter(owned_offers, Candidate.deleted_at.is_(None))
            .order_by(MatchResult.score_global.desc(), Application.applied_at.desc())
            .limit(5)
            .all()
        )
        audit_candidate_identity_reads(
            db,
            actor_user_id=getattr(employer, "user_id", None),
            employer_id=employer.id,
            applications=[
                (application, offer, candidate, pii, match)
                for application, offer, candidate, pii, match in top_candidate_rows
            ],
        )
        top_candidates = [
            DashboardTopCandidate(
                application_id=str(application.id),
                candidate_name=pii.full_name if pii else None,
                offer_title=offer.title,
                score_global=float(match.score_global),
                status=application.status.value,
            )
            for application, offer, _candidate, pii, match in top_candidate_rows
        ]

        offer_rows = (
            db.query(
                JobOffer,
                func.count(Application.id),
                func.max(MatchResult.score_global),
            )
            .outerjoin(Application, Application.job_offer_id == JobOffer.id)
            .outerjoin(MatchResult, MatchResult.id == Application.match_result_id)
            .filter(
                owned_offers,
                JobOffer.status == OfferStatus.PUBLISHED,
                JobOffer.archived_at.is_(None),
            )
            .group_by(JobOffer.id)
            .order_by(JobOffer.published_at.desc().nullslast(), JobOffer.created_at.desc())
            .limit(4)
            .all()
        )
        offers_snapshot = [
            DashboardOfferSnapshot(
                offer_id=str(offer.id),
                title=offer.title,
                applications_count=applications_count or 0,
                top_match_score=float(top_score) if top_score is not None else None,
                expires_at=_utc_iso(offer.expires_at),
            )
            for offer, applications_count, top_score in offer_rows
        ]

        benchmarkable = (
            db.query(JobOffer, Occupation)
            .join(Occupation, Occupation.id == JobOffer.occupation_id)
            .filter(
                owned_offers,
                JobOffer.status == OfferStatus.PUBLISHED,
                JobOffer.archived_at.is_(None),
                JobOffer.governorate_code.is_not(None),
            )
            .order_by(JobOffer.published_at.desc().nullslast(), JobOffer.created_at.desc())
            .first()
        )

        return EmployerDashboard(
            kpis=DashboardKpis(
                active_offers=active_offers,
                applications_total=application_totals[0] or 0,
                shortlisted=application_totals[1] or 0,
                hired=application_totals[2] or 0,
                average_match_score=float(scored_average) if scored_average is not None else None,
                next_interview_at=_utc_iso(next_interview),
            ),
            attention=attention,
            top_candidates=top_candidates,
            offers_snapshot=offers_snapshot,
            latest_benchmarkable_offer=(
                BenchmarkableOffer(
                    offer_id=str(benchmarkable[0].id),
                    occupation_code=benchmarkable[1].code,
                    governorate_code=benchmarkable[0].governorate_code,
                )
                if benchmarkable
                else None
            ),
        )

    @router.get("/api/v1/employer/interviews", response_model=list[InterviewInvitation])
    def list_employer_interviews(
        status_filter: DeliveryStatus | None = Query(default=None, alias="status"),
        upcoming: bool = False,
        db: Session = Depends(get_db),
        employer: Employer = Depends(get_current_employer),
    ) -> list[InterviewInvitation]:
        query = (
            db.query(NotificationOutbox, Application, JobOffer, Candidate, CandidatePII)
            .join(Application, Application.id == NotificationOutbox.application_id)
            .join(JobOffer, JobOffer.id == Application.job_offer_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .outerjoin(CandidatePII, CandidatePII.candidate_id == Candidate.id)
            .filter(
                NotificationOutbox.employer_id == employer.id,
                JobOffer.employer_id == employer.id,
                Candidate.deleted_at.is_(None),
            )
        )
        if status_filter is not None:
            query = query.filter(NotificationOutbox.status == status_filter)
        if upcoming:
            query = query.filter(NotificationOutbox.meeting_at >= datetime.now(timezone.utc))
        rows = query.order_by(NotificationOutbox.meeting_at.asc(), NotificationOutbox.created_at.desc()).all()
        audit_candidate_identity_reads(
            db,
            actor_user_id=getattr(employer, "user_id", None),
            employer_id=employer.id,
            applications=[
                (application, offer, candidate, pii, None)
                for _invitation, application, offer, candidate, pii in rows
            ],
        )
        return [
            InterviewInvitation(
                invitation_id=str(invitation.id),
                application_id=str(application.id),
                candidate_name=pii.full_name if pii else None,
                offer_title=offer.title,
                meeting_at=_utc_iso(invitation.meeting_at) or "",
                timezone=invitation.meeting_timezone,
                status=invitation.status,
            )
            for invitation, application, offer, _candidate, pii in rows
        ]

    @router.get("/api/v1/employer/offers/counts", response_model=EmployerOfferCounts)
    def employer_offer_counts(
        db: Session = Depends(get_db),
        employer: Employer = Depends(get_current_employer),
    ) -> EmployerOfferCounts:
        all_offers = db.query(func.count(JobOffer.id)).filter(JobOffer.employer_id == employer.id).scalar() or 0
        published = db.query(func.count(JobOffer.id)).filter(
            JobOffer.employer_id == employer.id,
            JobOffer.status == OfferStatus.PUBLISHED,
            JobOffer.archived_at.is_(None),
        ).scalar() or 0
        archived = db.query(func.count(JobOffer.id)).filter(
            JobOffer.employer_id == employer.id,
            JobOffer.archived_at.is_not(None),
        ).scalar() or 0
        draft_status = EmployerDraftSession.draft["status"].as_string()
        drafts = db.query(func.count(EmployerDraftSession.id)).filter(
            EmployerDraftSession.employer_id == employer.id,
            or_(
                EmployerDraftSession.draft.is_(None),
                draft_status.is_(None),
                draft_status != "published",
            ),
        ).scalar() or 0
        return EmployerOfferCounts(
            all=int(all_offers + drafts),
            published=int(published),
            drafts=int(drafts),
            archived=int(archived),
        )

    @router.get("/api/v1/employer/catalogs/skills", response_model=list[SkillCatalogItem])
    def employer_skill_catalog(
        q: str = Query(default="", max_length=200),
        limit: int = Query(default=20, ge=1, le=100),
        db: Session = Depends(get_db),
        _employer: Employer = Depends(get_current_employer),
    ) -> list[SkillCatalogItem]:
        return [
            SkillCatalogItem(skill_code=skill.code, label=skill.label_fr)
            for skill in search_skills(db, q, limit=limit)
        ]

    @router.get("/api/v1/employer/catalogs/languages", response_model=LanguageCatalog)
    def employer_language_catalog(
        _employer: Employer = Depends(get_current_employer),
    ) -> LanguageCatalog:
        return LanguageCatalog(languages=list(SUPPORTED_LANGUAGES), levels=list(LANGUAGE_LEVELS))

    return router
