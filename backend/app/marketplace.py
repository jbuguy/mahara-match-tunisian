from collections import Counter
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import Depends
from sqlalchemy.sql.elements import ColumnElement

from app.audit import record_audit_event, record_sensitive_read
from app.database import get_session
from app.dependencies import require_permission
from app.locations import validate_location
from app.skill_catalog import recognised_skill_share, sync_course_skills
from app.analytics import AnalyticsFilters, analytics_meta, candidates_per_open_position, median, percentage_share, previous_period, sparkline, suppress_small, time_to_hire_bin
from app.models import ApplicationStatusEvent, CandidateSkill, CourseSkill, Governorate, NationalIndicator, OfferSkill, OrganisationMembership, SkillCatalogue
from app.observatory_config import OBSERVATORY_CONFIG, skills_gap_status
from app.models import (
    CandidateProfile,
    EmployerNotification,
    EmployerNotificationPreference,
    CourseEnrollment,
    CourseEnrollmentStatus,
    CourseDeliveryMode,
    CourseStatus,
    JobApplication,
    JobApplicationStatusHistory,
    record_application_status_event,
    JobOfferStatus,
    JobApplicationStatus,
    JobOffer,
    Organisation,
    Role,
    TrainingCourse,
    User,
)
from app.knowledge_base import KnowledgeDocument
from app.permissions import Permission
from app.schemas import (
    AdminIndicatorsResponse,
    ApplicationStatusIndicator,
    CourseEnrollmentResponse,
    CourseEnrollmentStatusUpdate,
    EmployerApplicationResponse,
    JobApplicationResponse,
    JobApplicationStatusUpdate,
    ApplicationStatusHistoryResponse,
    ProviderCourseEnrollmentResponse,
    SkillDemandIndicator,
    TrainingCourseCreate,
    TrainingCourseResponse,
    PublicTrainingCourseResponse,
    PublicTrainingSearchPage,
)

router = APIRouter()


@router.post("/admin/observatory/export-audit", tags=["administration"])
def admin_observatory_export_audit(
    payload: dict[str, object],
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    export_type = payload.get("export_type")
    if export_type not in {"csv", "pdf"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="export_type must be csv or pdf.")
    record_audit_event(
        session,
        action=f"observatory.export.{export_type}",
        actor=user,
        resource_type="observatory_dashboard",
        resource_id=str(payload.get("chart") or payload.get("section") or "dashboard"),
        details={
            "export_type": export_type,
            "filters": payload.get("filters") or {},
            "chart": payload.get("chart"),
            "section": payload.get("section"),
        },
    )
    session.commit()
    return {"status": "logged"}


def _analytics_count(session: Session, statement):
    return session.scalar(statement) or 0


@router.get("/admin/observatory", tags=["administration"])
def admin_observatory(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    period = {"start_date": filters.start_date, "end_date": filters.end_date}
    previous = previous_period(filters.start_date, filters.end_date)

    candidate_filters = [
        User.role == Role.CANDIDATE,
        *_date_window(User.created_at, filters.start_date, filters.end_date),
    ]
    if filters.governorate_code:
        candidate_filters.append(CandidateProfile.governorate_code == filters.governorate_code)
    if filters.age_group:
        reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
        if filters.age_group == "15-24":
            candidate_filters.append(CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15))
        elif filters.age_group == "25-34":
            candidate_filters.append(CandidateProfile.birth_year.between(reference_year - 34, reference_year - 25))
        else:
            candidate_filters.append(CandidateProfile.birth_year <= reference_year - 35)
    governorate_rows = session.execute(
        select(CandidateProfile.governorate_code, func.count())
        .join(User, User.id == CandidateProfile.user_id)
        .where(*candidate_filters, CandidateProfile.governorate_code.is_not(None))
        .group_by(CandidateProfile.governorate_code)
    )
    governorates = [
        {"governorate_code": code, **suppress_small(count)}
        for code, count in governorate_rows
    ]

    sector_filters = [
        *_date_window(JobOffer.created_at, filters.start_date, filters.end_date),
    ]
    sector_filters.append(OrganisationMembership.organisation_id == Organisation.id)
    sector_filters.append(OrganisationMembership.user_id == JobOffer.employer_id)
    if filters.governorate_code:
        sector_filters.append(JobOffer.governorate_code == filters.governorate_code)
    if filters.sector_code:
        sector_filters.append(func.lower(Organisation.sector) == filters.sector_code.casefold())
    sector_rows = session.execute(
        select(Organisation.sector, func.count())
        .join(OrganisationMembership, OrganisationMembership.organisation_id == Organisation.id)
        .join(JobOffer, JobOffer.employer_id == OrganisationMembership.user_id)
        .where(*sector_filters, Organisation.sector.is_not(None))
        .group_by(Organisation.sector)
    )
    sectors = [
        {"sector_code": sector, **suppress_small(count)}
        for sector, count in sector_rows
    ]

    profile_filters = [
        CandidateProfile.birth_year.is_not(None),
        *_date_window(User.created_at, filters.start_date, filters.end_date),
    ]
    if filters.governorate_code:
        profile_filters.append(CandidateProfile.governorate_code == filters.governorate_code)
    profiles = list(session.execute(
        select(CandidateProfile.birth_year)
        .join(User, User.id == CandidateProfile.user_id)
        .where(*profile_filters)
    ))
    age_counts = {"15-24": 0, "25-34": 0, "35+": 0}
    reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
    for (birth_year,) in profiles:
        age = reference_year - birth_year
        group = "15-24" if 15 <= age <= 24 else "25-34" if 25 <= age <= 34 else "35+" if age >= 35 else None
        if group:
            age_counts[group] += 1
    age_groups = [
        {"age_group": group, **suppress_small(count)}
        for group, count in age_counts.items()
    ]

    skill_filters = [
        User.role == Role.CANDIDATE,
        *_date_window(User.created_at, filters.start_date, filters.end_date),
    ]
    if filters.governorate_code:
        skill_filters.append(CandidateProfile.governorate_code == filters.governorate_code)
    skill_rows = session.execute(
        select(SkillCatalogue.canonical_name_fr, func.count(CandidateSkill.user_id))
        .join(CandidateSkill, CandidateSkill.skill_id == SkillCatalogue.id)
        .join(CandidateProfile, CandidateProfile.user_id == CandidateSkill.user_id)
        .join(User, User.id == CandidateProfile.user_id)
        .where(*skill_filters)
        .group_by(SkillCatalogue.id, SkillCatalogue.canonical_name_fr)
        .order_by(func.count(CandidateSkill.user_id).desc())
        .limit(25)
    )
    skills = [
        {"skill": name, **suppress_small(count)}
        for name, count in skill_rows
    ]

    current_total = _analytics_count(
        session,
        select(func.count())
        .select_from(User)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(*candidate_filters),
    )
    previous_filters = [
        User.role == Role.CANDIDATE,
        *_date_window(User.created_at, previous["start_date"], previous["end_date"]),
    ]
    if filters.governorate_code:
        previous_filters.append(CandidateProfile.governorate_code == filters.governorate_code)
    if filters.age_group:
        reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
        if filters.age_group == "15-24":
            previous_filters.append(CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15))
        elif filters.age_group == "25-34":
            previous_filters.append(CandidateProfile.birth_year.between(reference_year - 34, reference_year - 25))
        else:
            previous_filters.append(CandidateProfile.birth_year <= reference_year - 35)
    previous_total = session.scalar(
        select(func.count())
        .select_from(User)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(*previous_filters)
    ) or 0

    return {
        "meta": analytics_meta(
            "Nombre de candidats enregistrés et répartition agrégée des compétences.",
            period,
        ),
        "comparison": {
            "period": period,
            "previous_period": previous,
            "value": suppress_small(current_total),
            "previous_value": suppress_small(previous_total),
        },
        "governorates": governorates,
        "sectors": sectors,
        "age_groups": age_groups,
        "skills": skills,
    }


def _analytics_candidate_filters(filters: AnalyticsFilters, period_start: date | None, period_end: date | None):
    conditions = [
        User.role == Role.CANDIDATE,
        *_date_window(User.created_at, period_start, period_end),
    ]
    if filters.governorate_code:
        conditions.append(CandidateProfile.governorate_code == filters.governorate_code)
    if filters.age_group:
        reference_year = period_end.year if period_end else datetime.now(timezone.utc).year
        if filters.age_group == "15-24":
            conditions.append(CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15))
        elif filters.age_group == "25-34":
            conditions.append(CandidateProfile.birth_year.between(reference_year - 34, reference_year - 25))
        else:
            conditions.append(CandidateProfile.birth_year <= reference_year - 35)
    return conditions


def _metric(value, previous, spark: list[int | float], definition: str) -> dict[str, object]:
    return {
        "value": suppress_small(value) if isinstance(value, int) else value,
        "previous_period_value": suppress_small(previous) if isinstance(previous, int) else previous,
        "sparkline": sparkline(spark),
        "definition": definition,
    }


@router.get("/admin/observatory/kpis", tags=["administration"])
def admin_observatory_kpis(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    previous = previous_period(filters.start_date, filters.end_date)
    period = {"start_date": filters.start_date, "end_date": filters.end_date}
    candidate_conditions = _analytics_candidate_filters(filters, filters.start_date, filters.end_date)
    active_candidates = session.scalar(
        select(func.count(func.distinct(User.id)))
        .select_from(User)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .outerjoin(JobApplication, JobApplication.candidate_id == User.id)
        .where(*candidate_conditions)
    ) or 0
    offer_conditions = [
        JobOffer.status == JobOfferStatus.PUBLISHED,
        JobOffer.application_deadline.is_(None) | (JobOffer.application_deadline >= date.today()),
        *_date_window(JobOffer.created_at, filters.start_date, filters.end_date),
    ]
    if filters.governorate_code:
        offer_conditions.append(JobOffer.governorate_code == filters.governorate_code)
    open_positions = session.scalar(
        select(func.coalesce(func.sum(JobOffer.positions_count), 0)).where(*offer_conditions)
    ) or 0
    previous_offer_conditions = [
        JobOffer.status == JobOfferStatus.PUBLISHED,
        JobOffer.application_deadline.is_(None) | (JobOffer.application_deadline >= date.today()),
        *_date_window(JobOffer.created_at, previous["start_date"], previous["end_date"]),
    ]
    if filters.governorate_code:
        previous_offer_conditions.append(JobOffer.governorate_code == filters.governorate_code)
    previous_open_positions = session.scalar(
        select(func.coalesce(func.sum(JobOffer.positions_count), 0)).where(*previous_offer_conditions)
    ) or 0
    closed_statuses = [JobApplicationStatus.HIRED, JobApplicationStatus.REJECTED, JobApplicationStatus.WITHDRAWN]
    closed = session.scalar(select(func.count(JobApplication.id)).where(JobApplication.status.in_(closed_statuses))) or 0
    hired = session.scalar(select(func.count(JobApplication.id)).where(JobApplication.status == JobApplicationStatus.HIRED)) or 0
    placement_rate = round(100 * hired / closed, 1) if closed else None
    previous_active_candidates = session.scalar(
        select(func.count(func.distinct(User.id)))
        .select_from(User)
        .where(*_analytics_candidate_filters(filters, previous["start_date"], previous["end_date"]))
    ) or 0

    hire_durations = []
    hire_rows = session.execute(
        select(ApplicationStatusEvent.application_id, ApplicationStatusEvent.changed_at)
        .where(ApplicationStatusEvent.to_status == JobApplicationStatus.HIRED.value, ApplicationStatusEvent.backfilled == False)
    )
    hired_at = {row.application_id: row.changed_at for row in hire_rows}
    submitted_rows = session.execute(
        select(ApplicationStatusEvent.application_id, ApplicationStatusEvent.changed_at)
        .where(ApplicationStatusEvent.to_status == JobApplicationStatus.SUBMITTED.value, ApplicationStatusEvent.backfilled == False)
    )
    submitted_at = {row.application_id: row.changed_at for row in submitted_rows}
    for application_id, hired_on in hired_at.items():
        submitted_on = submitted_at.get(application_id)
        if submitted_on:
            hire_durations.append(max(0, (hired_on.date() - submitted_on.date()).days))

    birth_profiles = list(session.execute(
        select(CandidateProfile.birth_year)
        .join(User, User.id == CandidateProfile.user_id)
        .where(User.role == Role.CANDIDATE)
    ))
    reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
    candidate_youth = sum(1 for (birth_year,) in birth_profiles if birth_year and 15 <= reference_year - birth_year <= 24)
    youth_share = round(100 * candidate_youth / len(birth_profiles), 1) if birth_profiles else None

    hires = session.scalars(
        select(JobApplication.candidate_id).where(JobApplication.status == JobApplicationStatus.HIRED)
    ).all()
    youth_hires = session.scalar(
        select(func.count(func.distinct(JobApplication.candidate_id)))
        .join(CandidateProfile, CandidateProfile.user_id == JobApplication.candidate_id)
        .where(
            JobApplication.status == JobApplicationStatus.HIRED,
            CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15),
        )
    ) or 0
    youth_hire_share = round(100 * youth_hires / len(set(hires)), 1) if hires else None

    completers = session.scalars(
        select(CourseEnrollment.candidate_id).where(CourseEnrollment.status == CourseEnrollmentStatus.COMPLETED)
    ).all()
    completer_ids = set(completers)
    converted = 0
    if completer_ids:
        enrollment_rows = session.execute(
            select(CourseEnrollment.candidate_id, CourseEnrollment.completed_at)
            .where(CourseEnrollment.candidate_id.in_(completer_ids), CourseEnrollment.status == CourseEnrollmentStatus.COMPLETED)
        )
        for candidate_id, completed_at in enrollment_rows:
            if completed_at and session.scalar(
                select(func.count()).select_from(JobApplication).where(
                    JobApplication.candidate_id == candidate_id,
                    JobApplication.created_at >= completed_at,
                    JobApplication.created_at <= completed_at + timedelta(days=90),
                )
            ):
                converted += 1
    training_rate = round(100 * converted / len(completer_ids), 1) if completer_ids else None

    return {
        "meta": analytics_meta("Indicateurs clés agrégés des candidats, des offres, des embauches et de la formation.", period, "/admin/observatory/kpis"),
        "previous_period": previous,
        "active_candidates": _metric(active_candidates, previous_active_candidates, [active_candidates] * 12, "Candidats ayant postulé ou mis à jour leur profil pendant la période."),
        "open_positions": _metric(open_positions, previous_open_positions, [open_positions] * 12, "Nombre de postes ouverts dans les offres publiées et non expirées."),
        "declared_placement_rate": _metric(placement_rate, None, [placement_rate or 0] * 12, "Part des candidatures closes recrutées, parmi les recrutements et refus enregistrés."),
        "median_days_to_hire": _metric(median(hire_durations), None, [median(hire_durations) or 0] * 12, "Délai médian entre la candidature et l'embauche."),
        "youth_share_of_candidates": _metric(youth_share, None, [youth_share or 0] * 12, "Part des candidats âgés de 15 à 24 ans."),
        "youth_share_of_hires": _metric(youth_hire_share, None, [youth_hire_share or 0] * 12, "Part des embauches concernées par des candidats âgés de 15 à 24 ans."),
        "training_to_job_rate": _metric(training_rate, None, [training_rate or 0] * 12, "Part des diplômés ayant postulé dans les quatre-vingt-dix jours suivant leur formation achevée."),
    }


@router.get("/admin/observatory/funnel", tags=["administration"])
def admin_observatory_funnel(
    youth: bool = Query(default=False),
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    period = {"start_date": filters.start_date, "end_date": filters.end_date}
    previous = previous_period(filters.start_date, filters.end_date)
    base = select(User.id).select_from(User).outerjoin(CandidateProfile, CandidateProfile.user_id == User.id).where(*_analytics_candidate_filters(filters, filters.start_date, filters.end_date))
    candidate_ids = {value for value in session.scalars(base).all()}
    if youth:
        reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
        candidate_ids &= set(session.scalars(
            select(CandidateProfile.user_id).where(CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15))
        ).all())

    status_aliases = {
        "registered": [],
        "profile_completed": [],
        "applied": ["submitted"],
        "shortlisted": ["shortlisted"],
        "interviewed": ["interview", "interview_completed", "interviewed"],
        "offered": ["offer_made", "offered"],
        "hired": ["hired"],
    }
    funnel: dict[str, int] = {}
    funnel["registered"] = len(candidate_ids)
    funnel["profile_completed"] = session.scalar(
        select(func.count(func.distinct(CandidateProfile.user_id)))
        .where(CandidateProfile.user_id.in_(candidate_ids), CandidateProfile.profile_completed_at.is_not(None))
    ) or 0
    for stage, aliases in status_aliases.items():
        if stage in {"registered", "profile_completed"}:
            continue
        event_filters = [
            ApplicationStatusEvent.to_status.in_(aliases),
            JobApplication.candidate_id.in_(candidate_ids),
            *_date_window(ApplicationStatusEvent.changed_at, filters.start_date, filters.end_date),
        ]
        funnel[stage] = session.scalar(
            select(func.count(func.distinct(JobApplication.candidate_id)))
            .select_from(ApplicationStatusEvent)
            .join(JobApplication, JobApplication.id == ApplicationStatusEvent.application_id)
            .where(*event_filters)
        ) or 0

    return {
        "meta": analytics_meta("Entonnoir de parcours distincts des candidats, construit à partir des événements de candidature.", period, "/admin/observatory/funnel"),
        "previous_period": previous,
        "youth": youth,
        "counts": {key: suppress_small(value) for key, value in funnel.items()},
        "sparkline": sparkline([funnel["registered"]] * 12),
    }


@router.get("/admin/observatory/time-to-hire", tags=["administration"])
def admin_observatory_time_to_hire(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    period = {"start_date": filters.start_date, "end_date": filters.end_date}
    previous = previous_period(filters.start_date, filters.end_date)
    event_rows = session.execute(
        select(
            ApplicationStatusEvent.application_id,
            ApplicationStatusEvent.to_status,
            ApplicationStatusEvent.changed_at,
        )
        .where(
            ApplicationStatusEvent.backfilled == False,
            *_date_window(ApplicationStatusEvent.changed_at, filters.start_date, filters.end_date),
        )
        .order_by(ApplicationStatusEvent.changed_at)
    )
    events_by_application: dict[str, dict[str, datetime | None]] = {}
    for application_id, status_value, changed_at in event_rows:
        events = events_by_application.setdefault(application_id, {})
        if status_value == "submitted":
            events["submitted"] = changed_at
        if status_value == "hired":
            events["hired"] = changed_at
        if status_value in {"interview", "interview_completed", "interviewed"}:
            events["interviewed"] = changed_at
    durations = []
    interviewed_applications = 0
    for events in events_by_application.values():
        if events.get("interviewed"):
            interviewed_applications += 1
        if events.get("submitted") and events.get("hired"):
            durations.append(max(0, (events["hired"].date() - events["submitted"].date()).days))
    bins = ["0-7", "8-14", "15-21", "22-30", "31-45", "46-60", "60+"]
    histogram = {label: 0 for label in bins}
    for duration in durations:
        histogram[time_to_hire_bin(duration)] += 1
    applications_with_events = len(events_by_application)
    interview_share = round(100 * interviewed_applications / applications_with_events, 1) if applications_with_events else None
    median_duration = median(durations)
    return {
        "meta": analytics_meta("Délai de recrutement, répartition des embauches et part des candidatures ayant connu un entretien; les événements reconstitués sont exclus.", period, "/admin/observatory/time-to-hire"),
        "previous_period": previous,
        "histogram": [
            {"bin": label, **suppress_small(count)}
            for label, count in histogram.items()
        ],
        "median_days": suppress_small(int(median_duration)) if median_duration is not None else {"value": None, "suppressed": False},
        "interview_share_percent": suppress_small(round(interview_share)) if interview_share is not None else {"value": None, "suppressed": False},
        "sparkline": sparkline(durations),
    }

_CLOSED_APPLICATION_STATUSES = {
    JobApplicationStatus.HIRED,
    JobApplicationStatus.REJECTED,
    JobApplicationStatus.WITHDRAWN,
}


@router.get("/admin/observatory/national-context", tags=["administration"])
def admin_national_context(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    indicator_names = {
        "total_unemployment": "Chômage total",
        "youth_unemployment_15_24": "Chômage des jeunes de 15 à 24 ans",
        "employment_to_population": "Emploi rapporté à la population",
        "agridata_jobs_created": "Emplois créés selon AgriData",
    }
    national = {}
    for indicator_id, label in indicator_names.items():
        rows = list(session.execute(
            select(NationalIndicator, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == NationalIndicator.source_document_id)
            .where(NationalIndicator.indicator_id == indicator_id)
            .order_by(NationalIndicator.year)
        ))
        if not rows:
            continue
        first_indicator, document = rows[0]
        national[indicator_id] = {
            "series": [{"year": row.year, "value": row.value} for row, _ in rows],
            "unit": first_indicator.unit,
            "methodology": document.document_metadata.get("methodology") or "Valeurs annuelles issues du document source.",
            "source": document.source,
            "source_url": document.source_url,
            "retrieved_at": document.document_metadata.get("retrieved_at") or document.updated_at,
            "definition": label + ", en Tunisie, sur les années disponibles.",
        }

    application_rows = session.execute(
        select(JobApplication.created_at)
        .where(*_date_window(JobApplication.created_at, filters.start_date, filters.end_date))
    ).scalars().all()
    offer_rows = session.execute(
        select(JobOffer.created_at, JobOffer.status)
        .where(*_date_window(JobOffer.created_at, filters.start_date, filters.end_date))
    ).all()
    application_months: Counter[str] = Counter(application.strftime("%Y-%m") for application in application_rows)
    offer_months: Counter[str] = Counter(created.strftime("%Y-%m") for created, offer_status in offer_rows if offer_status == JobOfferStatus.PUBLISHED)

    monthly = sorted(set(application_months) | set(offer_months))
    return {
        "national": national,
        "platform": {
            "applications": {
                "series": [{"month": month, "value": application_months[month]} for month in monthly],
                "unit": "applications",
                "methodology": "Nombre mensuel de candidatures créées sur Mahara Match.",
                "source": "Mahara Match platform",
                "source_url": "/admin/observatory/national-context",
                "retrieved_at": datetime.now(timezone.utc),
            },
            "published_offers": {
                "series": [{"month": month, "value": offer_months[month]} for month in monthly],
                "unit": "offers",
                "methodology": "Nombre mensuel d'offres publiées sur Mahara Match.",
                "source": "Mahara Match platform",
                "source_url": "/admin/observatory/national-context",
                "retrieved_at": datetime.now(timezone.utc),
            },
        },
        "meta": analytics_meta(
            "Contexte national annuel et activité mensuelle de la plateforme, présentés séparément.",
            {"start_date": filters.start_date, "end_date": filters.end_date},
            "/admin/observatory/national-context",
        ),
    }


def _governorate_youth_filter(column, filters: AnalyticsFilters) -> list[object]:
    reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
    return [column.between(reference_year - 24, reference_year - 15)]


def _privacy_ratio(candidate_count: int, position_count: int) -> dict[str, object]:
    if position_count == 0:
        return {"value": None, "reason": "no_open_positions"}
    if 0 < candidate_count < 5 or 0 < position_count < 5:
        return {"value": None, "suppressed": True}
    return {"value": round(candidate_count / position_count, 2), "suppressed": False}


@router.get("/admin/observatory/governorates", tags=["administration"])
def admin_observatory_governorates(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    governorates = session.scalars(select(Governorate).order_by(Governorate.code)).all()
    rows = []
    for governorate in governorates:
        candidates = session.scalar(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(CandidateProfile, CandidateProfile.user_id == User.id)
            .where(
                User.role == Role.CANDIDATE,
                CandidateProfile.governorate_code == governorate.code,
                *_date_window(User.created_at, filters.start_date, filters.end_date),
            )
        ) or 0
        open_positions = session.scalar(
            select(func.coalesce(func.sum(JobOffer.positions_count), 0))
            .where(
                JobOffer.governorate_code == governorate.code,
                JobOffer.status == JobOfferStatus.PUBLISHED,
                *_date_window(JobOffer.created_at, filters.start_date, filters.end_date),
            )
        ) or 0
        published_courses = session.scalar(
            select(func.count(TrainingCourse.id)).where(
                TrainingCourse.governorate_code == governorate.code,
                TrainingCourse.status == CourseStatus.PUBLISHED,
                *_date_window(TrainingCourse.published_at, filters.start_date, filters.end_date),
            )
        ) or 0
        course_seats = session.scalar(
            select(func.coalesce(func.sum(TrainingCourse.capacity), 0)).where(
                TrainingCourse.governorate_code == governorate.code,
                TrainingCourse.status == CourseStatus.PUBLISHED,
                *_date_window(TrainingCourse.published_at, filters.start_date, filters.end_date),
            )
        ) or 0
        applications = session.scalar(
            select(func.count(func.distinct(JobApplication.id)))
            .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
            .where(
                JobOffer.governorate_code == governorate.code,
                *_date_window(JobApplication.created_at, filters.start_date, filters.end_date),
            )
        ) or 0
        hires = session.scalar(
            select(func.count(func.distinct(JobApplication.id)))
            .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
            .where(
                JobOffer.governorate_code == governorate.code,
                JobApplication.status == JobApplicationStatus.HIRED,
                *_date_window(JobApplication.updated_at, filters.start_date, filters.end_date),
            )
        ) or 0
        youth_candidates = session.scalar(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(CandidateProfile, CandidateProfile.user_id == User.id)
            .where(
                User.role == Role.CANDIDATE,
                CandidateProfile.governorate_code == governorate.code,
                *_governorate_youth_filter(CandidateProfile.birth_year, filters),
                *_date_window(User.created_at, filters.start_date, filters.end_date),
            )
        ) or 0
        youth_hires = session.scalar(
            select(func.count(func.distinct(JobApplication.candidate_id)))
            .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
            .join(CandidateProfile, CandidateProfile.user_id == JobApplication.candidate_id)
            .where(
                JobOffer.governorate_code == governorate.code,
                JobApplication.status == JobApplicationStatus.HIRED,
                *_governorate_youth_filter(CandidateProfile.birth_year, filters),
                *_date_window(JobApplication.updated_at, filters.start_date, filters.end_date),
            )
        ) or 0
        rows.append({
            "code": governorate.code,
            "name_fr": governorate.name_fr,
            "name_ar": governorate.name_ar,
            "candidates": suppress_small(candidates),
            "open_positions": suppress_small(open_positions),
            "published_courses": suppress_small(published_courses),
            "course_seats": suppress_small(course_seats),
            "applications": suppress_small(applications),
            "hires": suppress_small(hires),
            "candidates_per_open_position": _privacy_ratio(candidates, open_positions),
            "youth_candidates": suppress_small(youth_candidates),
            "youth_hires": suppress_small(youth_hires),
        })

    unspecified_counts = {
        "candidates": session.scalar(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(CandidateProfile, CandidateProfile.user_id == User.id)
            .where(User.role == Role.CANDIDATE, CandidateProfile.governorate_code.is_(None), *_date_window(User.created_at, filters.start_date, filters.end_date))
        ) or 0,
        "open_positions": session.scalar(
            select(func.coalesce(func.sum(JobOffer.positions_count), 0)).where(JobOffer.governorate_code.is_(None), JobOffer.status == JobOfferStatus.PUBLISHED, *_date_window(JobOffer.created_at, filters.start_date, filters.end_date))
        ) or 0,
        "published_courses": session.scalar(
            select(func.count(TrainingCourse.id)).where(TrainingCourse.governorate_code.is_(None), TrainingCourse.status == CourseStatus.PUBLISHED, *_date_window(TrainingCourse.published_at, filters.start_date, filters.end_date))
        ) or 0,
        "applications": session.scalar(
            select(func.count(func.distinct(JobApplication.id))).select_from(JobApplication).join(JobOffer, JobOffer.id == JobApplication.job_offer_id).where(JobOffer.governorate_code.is_(None), *_date_window(JobApplication.created_at, filters.start_date, filters.end_date))
        ) or 0,
        "course_seats": session.scalar(
            select(func.coalesce(func.sum(TrainingCourse.capacity), 0)).where(TrainingCourse.governorate_code.is_(None), TrainingCourse.status == CourseStatus.PUBLISHED, *_date_window(TrainingCourse.published_at, filters.start_date, filters.end_date))
        ) or 0,
        "hires": session.scalar(
            select(func.count(func.distinct(JobApplication.id))).select_from(JobApplication).join(JobOffer, JobOffer.id == JobApplication.job_offer_id).where(JobOffer.governorate_code.is_(None), JobApplication.status == JobApplicationStatus.HIRED, *_date_window(JobApplication.updated_at, filters.start_date, filters.end_date))
        ) or 0,
    }
    reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
    unspecified_counts["youth_candidates"] = session.scalar(
        select(func.count(func.distinct(User.id)))
        .select_from(User)
        .join(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(User.role == Role.CANDIDATE, CandidateProfile.governorate_code.is_(None), CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15), *_date_window(User.created_at, filters.start_date, filters.end_date))
    ) or 0
    unspecified_counts["youth_hires"] = session.scalar(
        select(func.count(func.distinct(JobApplication.candidate_id)))
        .select_from(JobApplication)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .join(CandidateProfile, CandidateProfile.user_id == JobApplication.candidate_id)
        .where(JobOffer.governorate_code.is_(None), CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15), JobApplication.status == JobApplicationStatus.HIRED, *_date_window(JobApplication.updated_at, filters.start_date, filters.end_date))
    ) or 0
    rows.append({
        "code": "unspecified",
        "name_fr": "Non spécifié",
        "name_ar": "غير محدد",
        **{key: suppress_small(value) for key, value in unspecified_counts.items()},
        "candidates_per_open_position": _privacy_ratio(
            unspecified_counts["candidates"],
            unspecified_counts["open_positions"],
        ),
    })
    return {
        "meta": analytics_meta("Répartition gouvernorale des indicateurs de marché du travail; les lignes sans gouvernorat sont comptées séparément.", {"start_date": filters.start_date, "end_date": filters.end_date}, "/admin/observatory/governorates"),
        "previous_period": previous_period(filters.start_date, filters.end_date),
        "rows": rows,
        "data_quality": {
            "unspecified_governorate": {key: suppress_small(value) for key, value in unspecified_counts.items()},
        },
    }


@router.get("/admin/observatory/youth-by-governorate", tags=["administration"])
def admin_observatory_youth_governorates(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    governorates = session.scalars(select(Governorate).order_by(Governorate.code)).all()
    reference_year = filters.end_date.year if filters.end_date else datetime.now(timezone.utc).year
    rows = []
    for governorate in governorates:
        youth_candidates = session.scalar(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(CandidateProfile, CandidateProfile.user_id == User.id)
            .where(User.role == Role.CANDIDATE, CandidateProfile.governorate_code == governorate.code, CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15), *_date_window(User.created_at, filters.start_date, filters.end_date))
        ) or 0
        youth_hires = session.scalar(
            select(func.count(func.distinct(JobApplication.candidate_id)))
            .join(CandidateProfile, CandidateProfile.user_id == JobApplication.candidate_id)
            .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
            .where(JobOffer.governorate_code == governorate.code, CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15), JobApplication.status == JobApplicationStatus.HIRED, *_date_window(JobApplication.updated_at, filters.start_date, filters.end_date))
        ) or 0
        rows.append({
            "code": governorate.code,
            "name_fr": governorate.name_fr,
            "name_ar": governorate.name_ar,
            "youth_candidates": suppress_small(youth_candidates),
            "youth_hires": suppress_small(youth_hires),
        })
    unspecified_youth_candidates = session.scalar(
        select(func.count(func.distinct(User.id)))
        .select_from(User)
        .join(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(User.role == Role.CANDIDATE, CandidateProfile.governorate_code.is_(None), CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15), *_date_window(User.created_at, filters.start_date, filters.end_date))
    ) or 0
    unspecified_youth_hires = session.scalar(
        select(func.count(func.distinct(JobApplication.candidate_id)))
        .join(CandidateProfile, CandidateProfile.user_id == JobApplication.candidate_id)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(JobOffer.governorate_code.is_(None), CandidateProfile.birth_year.between(reference_year - 24, reference_year - 15), JobApplication.status == JobApplicationStatus.HIRED, *_date_window(JobApplication.updated_at, filters.start_date, filters.end_date))
    ) or 0
    rows.append({
        "code": "unspecified",
        "name_fr": "Non spécifié",
        "name_ar": "غير محدد",
        "youth_candidates": suppress_small(unspecified_youth_candidates),
        "youth_hires": suppress_small(unspecified_youth_hires),
    })
    return {
        "meta": analytics_meta("Répartition des candidats jeunes et des embauches jeunes par gouvernorat.", {"start_date": filters.start_date, "end_date": filters.end_date}, "/admin/observatory/youth-by-governorate"),
        "previous_period": previous_period(filters.start_date, filters.end_date),
        "rows": rows,
    }


@router.get("/admin/observatory/skills-gap", tags=["administration"])
def admin_observatory_skills_gap(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    offer_rows = session.execute(
        select(OfferSkill.skill_id, func.count(func.distinct(OfferSkill.offer_id)))
        .join(JobOffer, JobOffer.id == OfferSkill.offer_id)
        .where(
            JobOffer.status == JobOfferStatus.PUBLISHED,
            OfferSkill.skill_type == "required",
            *_date_window(JobOffer.created_at, filters.start_date, filters.end_date),
        )
        .group_by(OfferSkill.skill_id)
    ).all()
    supply_rows = dict(session.execute(
        select(CandidateSkill.skill_id, func.count(func.distinct(CandidateSkill.user_id)))
        .group_by(CandidateSkill.skill_id)
    ).all())
    demand_rows = dict(offer_rows)
    skills = session.scalars(select(SkillCatalogue).where(SkillCatalogue.id.in_(demand_rows))).all()
    names = {skill.id: skill.canonical_name_fr for skill in skills}
    limit = OBSERVATORY_CONFIG["skills_gap"]["top_limit"]
    suppression_threshold = OBSERVATORY_CONFIG["skills_gap"]["supply_suppression_threshold"]
    ranked = sorted(demand_rows.items(), key=lambda item: (-item[1], names.get(item[0], "")))[:limit]
    rows = []
    for skill_id, demand in ranked:
        supply = supply_rows.get(skill_id, 0)
        supply_result = suppress_small(supply, k=suppression_threshold)
        rows.append({
            "skill_id": skill_id,
            "canonical_name_fr": names.get(skill_id),
            "demand": demand,
            "supply": supply_result,
            "status": skills_gap_status(demand, supply),
        })
    return {
        "meta": analytics_meta(
            "Comparaison de la demande publiée de compétences avec l'offre déclarée par les candidats.",
            {"start_date": filters.start_date, "end_date": filters.end_date},
            "/admin/observatory/skills-gap",
        ),
        "previous_period": previous_period(filters.start_date, filters.end_date),
        "rows": rows,
    }


@router.get("/admin/observatory/training-alignment", tags=["administration"])
def admin_observatory_training_alignment(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    demand_rows = session.execute(
        select(OfferSkill.skill_id, func.count(func.distinct(OfferSkill.offer_id)))
        .join(JobOffer, JobOffer.id == OfferSkill.offer_id)
        .where(
            JobOffer.status == JobOfferStatus.PUBLISHED,
            OfferSkill.skill_type == "required",
            *_date_window(JobOffer.created_at, filters.start_date, filters.end_date),
        )
        .group_by(OfferSkill.skill_id)
    ).all()
    limit = OBSERVATORY_CONFIG["skills_gap"]["top_limit"]
    top_ids = [skill_id for skill_id, _ in sorted(demand_rows, key=lambda item: (-item[1], item[0]))[:limit]]
    skills = session.scalars(select(SkillCatalogue).where(SkillCatalogue.id.in_(top_ids))).all()
    names = {skill.id: skill.canonical_name_fr for skill in skills}
    sector_map = OBSERVATORY_CONFIG["skill_sector_catalogue"]
    rows = []
    for skill_id in top_ids:
        demand = dict(demand_rows)[skill_id]
        course_ids = session.scalars(
            select(CourseSkill.course_id)
            .join(TrainingCourse, TrainingCourse.id == CourseSkill.course_id)
            .where(CourseSkill.skill_id == skill_id, TrainingCourse.status == CourseStatus.PUBLISHED)
        ).all()
        course_count = len(set(course_ids))
        total_seats = session.scalar(
            select(func.coalesce(func.sum(TrainingCourse.capacity), 0))
            .join(CourseSkill, CourseSkill.course_id == TrainingCourse.id)
            .where(CourseSkill.skill_id == skill_id, TrainingCourse.status == CourseStatus.PUBLISHED)
        ) or 0
        active_enrollments = session.scalar(
            select(func.count(CourseEnrollment.id))
            .join(CourseSkill, CourseSkill.course_id == CourseEnrollment.course_id)
            .where(CourseSkill.skill_id == skill_id, CourseEnrollment.status == CourseEnrollmentStatus.ENROLLED)
        ) or 0
        completed = session.scalar(
            select(func.count(CourseEnrollment.id))
            .join(CourseSkill, CourseSkill.course_id == CourseEnrollment.course_id)
            .where(CourseSkill.skill_id == skill_id, CourseEnrollment.status == CourseEnrollmentStatus.COMPLETED)
        ) or 0
        total_enrollments = session.scalar(
            select(func.count(CourseEnrollment.id))
            .join(CourseSkill, CourseSkill.course_id == CourseEnrollment.course_id)
            .where(CourseSkill.skill_id == skill_id)
        ) or 0
        completion_rate = round(completed / total_enrollments, 4) if total_enrollments else 0.0
        if course_count == 0:
            coverage_status = "none"
        elif total_seats < demand * OBSERVATORY_CONFIG["training_alignment"]["under_covered_seats_ratio"]:
            coverage_status = "under_covered"
        else:
            coverage_status = "covered"
        canonical_name = names.get(skill_id)
        rows.append({
            "skill_id": skill_id,
            "canonical_name_fr": canonical_name,
            "sectors": sector_map.get(canonical_name, []),
            "demand": demand,
            "published_courses": suppress_small(course_count),
            "total_seats": suppress_small(total_seats),
            "active_enrollments": suppress_small(active_enrollments),
            "completion_rate": completion_rate,
            "coverage_status": coverage_status,
        })
    year = OBSERVATORY_CONFIG["training_alignment"]["sector_taxonomy_year"]
    return {
        "meta": analytics_meta(
            "Alignement entre la demande de compétences publiées et l'offre de formation.",
            {"start_date": filters.start_date, "end_date": filters.end_date},
            "/admin/observatory/training-alignment",
        ),
        "taxonomy_2017_historical": True,
        "taxonomy_note": f"La nomenclature sectorielle {year} est historique et sert uniquement à nommer les secteurs; elle ne décrit pas une classification nationale actualisée.",
        "previous_period": previous_period(filters.start_date, filters.end_date),
        "rows": rows,
    }


def _employer_quality_warnings(
    no_decision_share: float | None,
    declared_outcome_share: float | None,
    governorate_share: float | None,
) -> list[str]:
    warnings = []
    threshold = OBSERVATORY_CONFIG["employer_quality"]
    if no_decision_share is not None and no_decision_share >= threshold["undecided_application_warning_share"]:
        warnings.append(
            f"{no_decision_share:.0f} % des candidatures sans décision : le taux de placement est probablement sous-estimé."
        )
    if declared_outcome_share is not None and declared_outcome_share < threshold["declared_outcome_warning_share"]:
        warnings.append(
            f"{declared_outcome_share:.0f} % des candidatures clôturées ont un résultat déclaré."
        )
    if governorate_share is not None and governorate_share < threshold["governorate_warning_share"]:
        warnings.append(
            f"{governorate_share:.0f} % des profils candidats déclarent un gouvernorat."
        )
    return warnings


@router.get("/admin/observatory/employers-quality", tags=["administration"])
def admin_observatory_employers_quality(
    filters: AnalyticsFilters = Depends(),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    offer_conditions = [*_date_window(JobOffer.created_at, filters.start_date, filters.end_date)]
    if filters.governorate_code:
        offer_conditions.append(JobOffer.governorate_code == filters.governorate_code)

    period_offers = session.scalars(select(JobOffer).where(*offer_conditions)).all()
    active_employer_ids = {offer.employer_id for offer in period_offers}
    active_organisations = session.scalar(
        select(func.count(func.distinct(OrganisationMembership.organisation_id)))
        .where(OrganisationMembership.user_id.in_(active_employer_ids))
    ) if active_employer_ids else 0

    offer_ids = [offer.id for offer in period_offers if offer.status != JobOfferStatus.DRAFT]
    published_ids = [offer.id for offer in period_offers if offer.status == JobOfferStatus.PUBLISHED]
    filled_offer_ids = set(session.scalars(
        select(JobApplication.job_offer_id)
        .where(
            JobApplication.job_offer_id.in_(offer_ids),
            JobApplication.status == JobApplicationStatus.HIRED,
        )
    ).all()) if offer_ids else set()
    expired = sum(
        1 for offer in period_offers
        if offer.status == JobOfferStatus.EXPIRED
        or offer.status == JobOfferStatus.CLOSED
        or offer.application_deadline is not None and offer.application_deadline < date.today()
    )
    still_open = sum(
        1 for offer in period_offers
        if offer.id in published_ids
        and offer.id not in filled_offer_ids
        and (
            offer.application_deadline is None
            or offer.application_deadline >= date.today()
        )
        and offer.status == JobOfferStatus.PUBLISHED
    )
    expired = sum(1 for offer in period_offers if offer.id not in filled_offer_ids and (offer.status == JobOfferStatus.EXPIRED or offer.status == JobOfferStatus.CLOSED or (offer.application_deadline is not None and offer.application_deadline < date.today())))
    filled = len(filled_offer_ids)
    outcome_denominator = filled + expired + still_open
    offer_outcomes = {
        "filled_share": percentage_share(filled, outcome_denominator),
        "expired_share": percentage_share(expired, outcome_denominator),
        "still_open_share": percentage_share(still_open, outcome_denominator),
    }

    application_conditions = [
        *_date_window(JobApplication.created_at, filters.start_date, filters.end_date),
    ]
    if filters.governorate_code:
        application_conditions.append(JobOffer.governorate_code == filters.governorate_code)
    application_count = session.scalar(
        select(func.count(func.distinct(JobApplication.id)))
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(*application_conditions)
    ) or 0
    decided_application_ids = set(session.scalars(
        select(JobApplicationStatusHistory.application_id)
        .where(
            JobApplicationStatusHistory.actor_id.is_not(None),
            JobApplicationStatusHistory.to_status != JobApplicationStatus.SUBMITTED,
        )
    ).all())
    responded_application_count = (
        session.scalar(
            select(func.count(func.distinct(JobApplication.id)))
            .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
            .where(*application_conditions, JobApplication.id.in_(decided_application_ids))
        )
        or 0
        if decided_application_ids
        else 0
    )
    undecided_application_count = application_count - responded_application_count
    employer_response_rate = percentage_share(responded_application_count, application_count)
    undecided_share = percentage_share(undecided_application_count, application_count)

    profile_conditions = [*_date_window(CandidateProfile.updated_at, filters.start_date, filters.end_date)]
    profiles_total = session.scalar(select(func.count()).select_from(CandidateProfile).where(*profile_conditions)) or 0
    profiles_with_governorate = session.scalar(
        select(func.count()).select_from(CandidateProfile)
        .where(*profile_conditions, CandidateProfile.governorate_code.is_not(None), func.trim(CandidateProfile.governorate_code) != "")
    ) or 0
    governorate_share = percentage_share(profiles_with_governorate, profiles_total)
    skill_share = round(100 * recognised_skill_share(session), 1)

    closed_statuses = [JobApplicationStatus.HIRED, JobApplicationStatus.REJECTED, JobApplicationStatus.WITHDRAWN]
    closed_applications = session.scalar(
        select(func.count(func.distinct(JobApplication.id)))
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(*application_conditions, JobApplication.status.in_(closed_statuses))
    ) or 0
    declared_outcomes = session.scalar(
        select(func.count(func.distinct(JobApplication.id)))
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(
            *application_conditions,
            JobApplication.status.in_([JobApplicationStatus.HIRED, JobApplicationStatus.REJECTED]),
        )
    ) or 0
    declared_outcome_share = percentage_share(declared_outcomes, closed_applications)
    warnings = _employer_quality_warnings(undecided_share, declared_outcome_share, governorate_share)

    return {
        "meta": analytics_meta(
            "Qualité de la réponse des employeurs et complétude des données de candidatures.",
            {"start_date": filters.start_date, "end_date": filters.end_date},
            "/admin/observatory/employers-quality",
        ),
        "previous_period": previous_period(filters.start_date, filters.end_date),
        "active_organisations": suppress_small(active_organisations),
        "offer_outcomes": offer_outcomes,
        "employer_response_rate": employer_response_rate,
        "applications_without_employer_decision_share": undecided_share,
        "candidate_profiles_with_governorate_share": governorate_share,
        "skills_recognised_share": skill_share,
        "closed_applications_with_declared_outcome_share": declared_outcome_share,
        "warnings": warnings,
    }


_EMPLOYER_APPLICATION_TRANSITIONS = {
    JobApplicationStatus.SUBMITTED: {
        JobApplicationStatus.REVIEWING,
        JobApplicationStatus.SHORTLISTED,
        JobApplicationStatus.INTERVIEW,
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.REVIEWING: {
        JobApplicationStatus.SHORTLISTED,
        JobApplicationStatus.INTERVIEW,
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.SHORTLISTED: {
        JobApplicationStatus.REVIEWING,
        JobApplicationStatus.INTERVIEW,
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.INTERVIEW: {
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.INTERVIEWED,
        JobApplicationStatus.OFFER_MADE,
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.INTERVIEW_COMPLETED: {
        JobApplicationStatus.OFFER_MADE,
        JobApplicationStatus.OFFERED,
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.OFFER_MADE: {
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.INTERVIEWED: {
        JobApplicationStatus.OFFERED,
        JobApplicationStatus.OFFER_MADE,
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
    JobApplicationStatus.OFFERED: {
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
    },
}


def _date_window(
    column: ColumnElement[datetime] | ColumnElement[datetime | None],
    start_date: date | None,
    end_date: date | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if start_date is not None:
        conditions.append(
            column >= datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        )
    if end_date is not None:
        conditions.append(
            column <= datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        )
    return conditions


def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The start date must be on or before the end date.",
        )


def _enrollment_counts(
    session: Session,
    course_ids: list[str],
) -> dict[str, tuple[int, int]]:
    if not course_ids:
        return {}
    rows = session.execute(
        select(CourseEnrollment.course_id, CourseEnrollment.status, func.count())
        .where(CourseEnrollment.course_id.in_(course_ids))
        .group_by(CourseEnrollment.course_id, CourseEnrollment.status)
    )
    counts: dict[str, tuple[int, int]] = {}
    for course_id, enrollment_status, count in rows:
        enrolled, completed = counts.get(course_id, (0, 0))
        if enrollment_status == CourseEnrollmentStatus.ENROLLED:
            enrolled = count
        elif enrollment_status == CourseEnrollmentStatus.COMPLETED:
            completed = count
        counts[course_id] = (enrolled, completed)
    return counts


def _course_response(
    course: TrainingCourse,
    counts: tuple[int, int] = (0, 0),
) -> TrainingCourseResponse:
    return TrainingCourseResponse.model_validate(course).model_copy(
        update={"enrollment_count": counts[0], "completed_count": counts[1]}
    )


def _candidate_application_response(
    application: JobApplication,
    offer: JobOffer,
) -> JobApplicationResponse:
    return JobApplicationResponse(
        id=application.id,
        job_offer_id=offer.id,
        job_title=offer.title,
        location=offer.location,
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.post(
    "/candidate/applications/{offer_id}",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["candidate applications"],
)
def apply_to_job(
    offer_id: str,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_OWN)),
    session: Session = Depends(get_session),
) -> JobApplicationResponse:
    offer = session.get(JobOffer, offer_id)
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job offer not found.")
    if offer.status != JobOfferStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This job offer is not accepting applications.",
        )
    application = JobApplication(
        candidate_id=user.id,
        job_offer_id=offer.id,
        status=JobApplicationStatus.SUBMITTED,
    )
    session.add(application)
    candidate_profile = session.get(CandidateProfile, user.id)
    if candidate_profile is not None:
        candidate_profile.last_active_at = datetime.now(timezone.utc)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        existing_application = session.scalar(
            select(JobApplication.id).where(
                JobApplication.candidate_id == user.id,
                JobApplication.job_offer_id == offer.id,
            )
        )
        if existing_application is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this offer.",
        ) from error
    record_audit_event(
        session,
        action="candidate.job_application.created",
        actor=user,
        resource_type="job_application",
        resource_id=application.id,
    )
    session.add(
        JobApplicationStatusHistory(
            application_id=application.id,
            actor_id=user.id,
            from_status=None,
            to_status=JobApplicationStatus.SUBMITTED,
        )
    )
    record_application_status_event(
        session, application, None, JobApplicationStatus.SUBMITTED, "system"
    )
    preference = session.get(EmployerNotificationPreference, (offer.employer_id, "application"))
    if preference is None or preference.enabled:
        session.add(
            EmployerNotification(
                user_id=offer.employer_id,
                notification_type="application",
                title="Nouvelle candidature",
                body=f"Une nouvelle candidature a été reçue pour {offer.title}.",
                resource_type="application",
                resource_id=application.id,
            )
        )
    session.commit()
    session.refresh(application)
    return _candidate_application_response(application, offer)


@router.get(
    "/employer/applications/{application_id}/history",
    response_model=list[ApplicationStatusHistoryResponse],
    tags=["employer applications"],
)
def employer_application_status_history(
    application_id: str,
    user: User = Depends(require_permission(Permission.APPLICANT_READ_BY_APPLICATION)),
    session: Session = Depends(get_session),
) -> list[ApplicationStatusHistoryResponse]:
    owns_application = session.scalar(
        select(JobApplication.id)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(JobApplication.id == application_id, JobOffer.employer_id == user.id)
    )
    if owns_application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    rows = session.scalars(
        select(JobApplicationStatusHistory)
        .where(JobApplicationStatusHistory.application_id == application_id)
        .order_by(JobApplicationStatusHistory.created_at, JobApplicationStatusHistory.id)
    )
    return [
        ApplicationStatusHistoryResponse(
            id=row.id,
            from_status=row.from_status,
            to_status=row.to_status,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get(
    "/candidate/applications",
    response_model=list[JobApplicationResponse],
    tags=["candidate applications"],
)
def candidate_applications(
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_OWN)),
    session: Session = Depends(get_session),
) -> list[JobApplicationResponse]:
    rows = session.execute(
        select(JobApplication, JobOffer)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(JobApplication.candidate_id == user.id)
        .order_by(JobApplication.created_at.desc())
    )
    return [
        _candidate_application_response(application, offer)
        for application, offer in rows
    ]


@router.post(
    "/candidate/applications/{application_id}/withdraw",
    response_model=JobApplicationResponse,
    tags=["candidate applications"],
)
def withdraw_candidate_application(
    application_id: str,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_OWN)),
    session: Session = Depends(get_session),
) -> JobApplicationResponse:
    row = session.execute(
        select(JobApplication, JobOffer)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(JobApplication.id == application_id, JobApplication.candidate_id == user.id)
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    application, offer = row
    if application.status in _CLOSED_APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This application already has a final outcome.",
        )
    previous_status = application.status
    application.status = JobApplicationStatus.WITHDRAWN
    record_application_status_event(
        session, application, previous_status, JobApplicationStatus.WITHDRAWN, "system"
    )
    session.add(
        JobApplicationStatusHistory(
            application_id=application.id,
            actor_id=user.id,
            from_status=previous_status,
            to_status=JobApplicationStatus.WITHDRAWN,
        )
    )
    record_audit_event(
        session,
        action="candidate.job_application.withdrawn",
        actor=user,
        resource_type="job_application",
        resource_id=application.id,
        details={"from": previous_status.value, "to": JobApplicationStatus.WITHDRAWN.value},
    )
    session.commit()
    session.refresh(application)
    return _candidate_application_response(application, offer)


@router.get(
    "/employer/applications",
    response_model=list[EmployerApplicationResponse],
    tags=["employer applications"],
)
def employer_applications(
    user: User = Depends(require_permission(Permission.APPLICANT_READ_BY_APPLICATION)),
    session: Session = Depends(get_session),
) -> list[EmployerApplicationResponse]:
    rows = session.execute(
        select(JobApplication, JobOffer, User, CandidateProfile)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .join(User, User.id == JobApplication.candidate_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(JobOffer.employer_id == user.id)
        .order_by(JobApplication.created_at.desc())
    )
    response: list[EmployerApplicationResponse] = []
    for application, offer, candidate, profile in rows:
        record_sensitive_read(
            session,
            actor=user,
            resource_type="job_applicant",
            resource_id=candidate.id,
        )
        response.append(
            EmployerApplicationResponse(
                id=application.id,
                job_offer_id=offer.id,
                job_title=offer.title,
                location=offer.location,
                status=application.status,
                created_at=application.created_at,
                updated_at=application.updated_at,
                candidate_name=profile.full_name if profile else None,
                candidate_location=profile.location if profile else None,
                candidate_skills=profile.skills if profile else [],
            )
        )
    if response:
        session.commit()
    return response


@router.put(
    "/employer/applications/{application_id}/status",
    response_model=JobApplicationResponse,
    tags=["employer applications"],
)
def update_application_status(
    application_id: str,
    request: JobApplicationStatusUpdate,
    user: User = Depends(require_permission(Permission.APPLICATION_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> JobApplicationResponse:
    row = session.execute(
        select(JobApplication, JobOffer)
        .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
        .where(
            JobApplication.id == application_id,
            JobOffer.employer_id == user.id,
        )
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    application, offer = row
    if application.status in _CLOSED_APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A closed application outcome cannot be changed.",
        )
    if request.status == JobApplicationStatus.WITHDRAWN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only the candidate can withdraw an application.",
        )
    previous_status = application.status
    if request.status not in _EMPLOYER_APPLICATION_TRANSITIONS.get(previous_status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot change an application from {previous_status.value} to {request.status.value}.",
        )
    application.status = request.status
    record_application_status_event(session, application, previous_status, request.status, "employer")
    session.add(
        JobApplicationStatusHistory(
            application_id=application.id,
            actor_id=user.id,
            from_status=previous_status,
            to_status=request.status,
        )
    )
    record_audit_event(
        session,
        action="employer.job_application.status_updated",
        actor=user,
        resource_type="job_application",
        resource_id=application.id,
        details={"from": previous_status.value, "to": request.status.value},
    )
    session.commit()
    session.refresh(application)
    return _candidate_application_response(application, offer)


@router.get(
    "/training/courses",
    response_model=list[TrainingCourseResponse],
    tags=["training provider"],
)
def provider_courses(
    user: User = Depends(require_permission(Permission.COURSE_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> list[TrainingCourseResponse]:
    courses = list(
        session.scalars(
            select(TrainingCourse)
            .where(TrainingCourse.provider_id == user.id)
            .order_by(TrainingCourse.updated_at.desc())
        )
    )
    counts = _enrollment_counts(session, [course.id for course in courses])
    return [_course_response(course, counts.get(course.id, (0, 0))) for course in courses]


@router.post(
    "/training/courses",
    response_model=TrainingCourseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["training provider"],
)
def create_course(
    request: TrainingCourseCreate,
    user: User = Depends(require_permission(Permission.COURSE_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> TrainingCourseResponse:
    validate_location(session, request.governorate_code, request.municipality_code)
    course = TrainingCourse(provider_id=user.id, **request.model_dump())
    if course.status == CourseStatus.PUBLISHED:
        course.published_at = datetime.now(timezone.utc)
    session.add(course)
    session.flush()
    course.skills = sync_course_skills(session, course.id, course.skills)
    record_audit_event(
        session,
        action="training.course.created",
        actor=user,
        resource_type="training_course",
        resource_id=course.id,
        details={"status": course.status.value, "skill_count": len(course.skills)},
    )
    session.commit()
    session.refresh(course)
    return _course_response(course)


@router.put(
    "/training/courses/{course_id}",
    response_model=TrainingCourseResponse,
    tags=["training provider"],
)
def update_course(
    course_id: str,
    request: TrainingCourseCreate,
    user: User = Depends(require_permission(Permission.COURSE_MANAGE_ORGANISATION)),
    session: Session = Depends(get_session),
) -> TrainingCourseResponse:
    validate_location(session, request.governorate_code, request.municipality_code)
    course = session.scalar(
        select(TrainingCourse).where(
            TrainingCourse.id == course_id,
            TrainingCourse.provider_id == user.id,
        ).with_for_update()
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    active_enrollments = session.scalar(
        select(func.count())
        .select_from(CourseEnrollment)
        .where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.status == CourseEnrollmentStatus.ENROLLED,
        )
    ) or 0
    if request.capacity < active_enrollments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Capacity cannot be lower than the current active enrollment count.",
        )
    previous_status = course.status
    for field, value in request.model_dump().items():
        setattr(course, field, value)
    course.skills = sync_course_skills(session, course.id, course.skills)
    if request.status == CourseStatus.PUBLISHED and previous_status != CourseStatus.PUBLISHED:
        course.published_at = datetime.now(timezone.utc)
    elif request.status != CourseStatus.PUBLISHED:
        course.published_at = None
    record_audit_event(
        session,
        action="training.course.updated",
        actor=user,
        resource_type="training_course",
        resource_id=course.id,
        details={"from_status": previous_status.value, "to_status": course.status.value},
    )
    session.commit()
    session.refresh(course)
    counts = _enrollment_counts(session, [course.id])
    return _course_response(course, counts.get(course.id, (0, 0)))


@router.get(
    "/training/courses/{course_id}/enrollments",
    response_model=list[ProviderCourseEnrollmentResponse],
    tags=["training provider"],
)
def provider_course_enrollments(
    course_id: str,
    user: User = Depends(
        require_permission(Permission.COURSE_ENROLLMENT_READ_ORGANISATION)
    ),
    session: Session = Depends(get_session),
) -> list[ProviderCourseEnrollmentResponse]:
    course = session.scalar(
        select(TrainingCourse).where(
            TrainingCourse.id == course_id,
            TrainingCourse.provider_id == user.id,
        )
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    rows = session.execute(
        select(CourseEnrollment, User, CandidateProfile)
        .join(User, User.id == CourseEnrollment.candidate_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(CourseEnrollment.course_id == course.id)
        .order_by(CourseEnrollment.created_at.desc())
    )
    enrollments: list[ProviderCourseEnrollmentResponse] = []
    for enrollment, candidate, profile in rows:
        record_sensitive_read(
            session,
            actor=user,
            resource_type="course_enrollee",
            resource_id=candidate.id,
        )
        enrollments.append(
            ProviderCourseEnrollmentResponse(
                id=enrollment.id,
                course_id=course.id,
                course_title=course.title,
                status=enrollment.status,
                created_at=enrollment.created_at,
                updated_at=enrollment.updated_at,
                candidate_name=profile.full_name if profile else None,
                candidate_location=profile.location if profile else None,
                candidate_skills=profile.skills if profile else [],
            )
        )
    if enrollments:
        session.commit()
    return enrollments


@router.put(
    "/training/enrollments/{enrollment_id}/status",
    response_model=ProviderCourseEnrollmentResponse,
    tags=["training provider"],
)
def update_course_enrollment(
    enrollment_id: str,
    request: CourseEnrollmentStatusUpdate,
    user: User = Depends(
        require_permission(Permission.COURSE_ENROLLMENT_MANAGE_ORGANISATION)
    ),
    session: Session = Depends(get_session),
) -> ProviderCourseEnrollmentResponse:
    row = session.execute(
        select(CourseEnrollment, TrainingCourse, User, CandidateProfile)
        .join(TrainingCourse, TrainingCourse.id == CourseEnrollment.course_id)
        .join(User, User.id == CourseEnrollment.candidate_id)
        .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(
            CourseEnrollment.id == enrollment_id,
            TrainingCourse.provider_id == user.id,
        )
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found.")
    enrollment, course, candidate, profile = row
    if (
        enrollment.status != CourseEnrollmentStatus.ENROLLED
        and enrollment.status != request.status
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A completed or withdrawn enrollment cannot be changed.",
        )
    record_sensitive_read(
        session,
        actor=user,
        resource_type="course_enrollee",
        resource_id=candidate.id,
    )
    previous_status = enrollment.status
    enrollment.status = request.status
    if request.status == CourseEnrollmentStatus.COMPLETED:
        enrollment.completed_at = datetime.now(timezone.utc)
    record_audit_event(
        session,
        action="training.enrollment.status_updated",
        actor=user,
        resource_type="course_enrollment",
        resource_id=enrollment.id,
        details={"from": previous_status.value, "to": request.status.value},
    )
    session.commit()
    session.refresh(enrollment)
    return ProviderCourseEnrollmentResponse(
        id=enrollment.id,
        course_id=course.id,
        course_title=course.title,
        status=enrollment.status,
        created_at=enrollment.created_at,
        updated_at=enrollment.updated_at,
        candidate_name=profile.full_name if profile else None,
        candidate_location=profile.location if profile else None,
        candidate_skills=profile.skills if profile else [],
    )


@router.get(
    "/candidate/courses",
    response_model=list[TrainingCourseResponse],
    tags=["candidate courses"],
)
def published_courses(
    user: User = Depends(require_permission(Permission.COURSE_READ_PUBLISHED)),
    session: Session = Depends(get_session),
) -> list[TrainingCourseResponse]:
    courses = list(
        session.scalars(
            select(TrainingCourse)
            .where(TrainingCourse.status == CourseStatus.PUBLISHED)
            .order_by(TrainingCourse.starts_on, TrainingCourse.created_at.desc())
        )
    )
    counts = _enrollment_counts(session, [course.id for course in courses])
    return [_course_response(course, counts.get(course.id, (0, 0))) for course in courses]


@router.get("/public/training", response_model=PublicTrainingSearchPage, tags=["public discovery"])
def public_training_search(
    q: str | None = Query(default=None, min_length=1, max_length=160),
    location: str | None = Query(default=None, min_length=1, max_length=120),
    delivery_mode: CourseDeliveryMode | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> PublicTrainingSearchPage:
    filters = [TrainingCourse.status == CourseStatus.PUBLISHED]
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            TrainingCourse.title.ilike(pattern)
            | TrainingCourse.summary.ilike(pattern)
            | TrainingCourse.location.ilike(pattern)
            | cast(TrainingCourse.skills, String).ilike(pattern)
        )
    if location:
        filters.append(TrainingCourse.location.ilike(f"%{location.strip()}%"))
    if delivery_mode is not None:
        filters.append(TrainingCourse.delivery_mode == delivery_mode)
    total = session.scalar(select(func.count()).select_from(TrainingCourse).where(*filters)) or 0
    courses = session.scalars(
        select(TrainingCourse)
        .where(*filters)
        .order_by(TrainingCourse.starts_on, TrainingCourse.created_at.desc(), TrainingCourse.id)
        .offset(offset)
        .limit(limit)
    )
    return PublicTrainingSearchPage(
        items=[PublicTrainingCourseResponse.model_validate(course) for course in courses],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/public/training/{course_id}", response_model=PublicTrainingCourseResponse, tags=["public discovery"])
def public_training_detail(
    course_id: str,
    session: Session = Depends(get_session),
) -> PublicTrainingCourseResponse:
    course = session.scalar(
        select(TrainingCourse).where(
            TrainingCourse.id == course_id,
            TrainingCourse.status == CourseStatus.PUBLISHED,
        )
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return PublicTrainingCourseResponse.model_validate(course)


@router.post(
    "/candidate/courses/{course_id}/enroll",
    response_model=CourseEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["candidate courses"],
)
def enroll_in_course(
    course_id: str,
    user: User = Depends(require_permission(Permission.COURSE_ENROLL)),
    session: Session = Depends(get_session),
) -> CourseEnrollmentResponse:
    course = session.scalar(
        select(TrainingCourse)
        .where(
            TrainingCourse.id == course_id,
            TrainingCourse.status == CourseStatus.PUBLISHED,
        )
        .with_for_update()
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    active_count = session.scalar(
        select(func.count())
        .select_from(CourseEnrollment)
        .where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.status == CourseEnrollmentStatus.ENROLLED,
        )
    ) or 0
    if active_count >= course.capacity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course is full.")
    enrollment = CourseEnrollment(
        candidate_id=user.id,
        course_id=course.id,
        status=CourseEnrollmentStatus.ENROLLED,
    )
    session.add(enrollment)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        existing_enrollment = session.scalar(
            select(CourseEnrollment.id).where(
                CourseEnrollment.candidate_id == user.id,
                CourseEnrollment.course_id == course.id,
            )
        )
        if existing_enrollment is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course.",
        ) from error
    record_audit_event(
        session,
        action="candidate.course.enrolled",
        actor=user,
        resource_type="course_enrollment",
        resource_id=enrollment.id,
    )
    session.commit()
    session.refresh(enrollment)
    return CourseEnrollmentResponse(
        id=enrollment.id,
        course_id=course.id,
        course_title=course.title,
        status=enrollment.status,
        created_at=enrollment.created_at,
        updated_at=enrollment.updated_at,
    )


@router.get(
    "/candidate/enrollments",
    response_model=list[CourseEnrollmentResponse],
    tags=["candidate courses"],
)
def candidate_enrollments(
    user: User = Depends(require_permission(Permission.COURSE_READ_PUBLISHED)),
    session: Session = Depends(get_session),
) -> list[CourseEnrollmentResponse]:
    rows = session.execute(
        select(CourseEnrollment, TrainingCourse)
        .join(TrainingCourse, TrainingCourse.id == CourseEnrollment.course_id)
        .where(CourseEnrollment.candidate_id == user.id)
        .order_by(CourseEnrollment.created_at.desc())
    )
    return [
        CourseEnrollmentResponse(
            id=enrollment.id,
            course_id=course.id,
            course_title=course.title,
            status=enrollment.status,
            created_at=enrollment.created_at,
            updated_at=enrollment.updated_at,
        )
        for enrollment, course in rows
    ]


@router.get(
    "/admin/indicators",
    response_model=AdminIndicatorsResponse,
    tags=["administration"],
)
def admin_indicators(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user: User = Depends(require_permission(Permission.INDICATOR_READ_AGGREGATE)),
    session: Session = Depends(get_session),
) -> AdminIndicatorsResponse:
    _validate_date_range(start_date, end_date)
    candidate_registrations = session.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.role == Role.CANDIDATE,
            *_date_window(User.created_at, start_date, end_date),
        )
    ) or 0
    organisations = session.scalar(
        select(func.count(Organisation.id)).where(
            *_date_window(Organisation.created_at, start_date, end_date)
        )
    ) or 0
    offers = list(
        session.scalars(
            select(JobOffer).where(
                JobOffer.status == JobOfferStatus.PUBLISHED,
                *_date_window(JobOffer.created_at, start_date, end_date),
            )
        )
    )
    application_rows = session.execute(
        select(JobApplication.status, func.count())
        .where(*_date_window(JobApplication.created_at, start_date, end_date))
        .group_by(JobApplication.status)
    )
    counts_by_status = {app_status: count for app_status, count in application_rows}
    applications_total = sum(counts_by_status.values())
    hired = counts_by_status.get(JobApplicationStatus.HIRED, 0)
    closed = (
        hired
        + counts_by_status.get(JobApplicationStatus.REJECTED, 0)
        + counts_by_status.get(JobApplicationStatus.WITHDRAWN, 0)
    )
    skills_by_key: dict[str, str] = {}
    skill_counts: Counter[str] = Counter()
    for offer in offers:
        skills_in_offer = {skill.strip().casefold(): skill.strip() for skill in offer.required_skills}
        for key, display in skills_in_offer.items():
            if key:
                skills_by_key.setdefault(key, display)
                skill_counts[key] += 1
    top_skills = [
        SkillDemandIndicator(skill=skills_by_key[key], offer_count=count)
        for key, count in sorted(skill_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    published_courses = session.scalar(
        select(func.count(TrainingCourse.id)).where(
            TrainingCourse.status == CourseStatus.PUBLISHED,
            *_date_window(TrainingCourse.published_at, start_date, end_date),
        )
    ) or 0
    active_enrollments = session.scalar(
        select(func.count(CourseEnrollment.id)).where(
            CourseEnrollment.status == CourseEnrollmentStatus.ENROLLED,
            *_date_window(CourseEnrollment.created_at, start_date, end_date),
        )
    ) or 0
    course_completions = session.scalar(
        select(func.count(CourseEnrollment.id)).where(
            CourseEnrollment.status == CourseEnrollmentStatus.COMPLETED,
            *_date_window(CourseEnrollment.updated_at, start_date, end_date),
        )
    ) or 0
    return AdminIndicatorsResponse(
        start_date=start_date,
        end_date=end_date,
        candidate_registrations=candidate_registrations,
        organisations=organisations,
        published_job_offers=len(offers),
        applications_total=applications_total,
        applications_by_status=[
            ApplicationStatusIndicator(status=app_status, count=count)
            for app_status, count in sorted(counts_by_status.items(), key=lambda item: item[0].value)
        ],
        closed_applications=closed,
        hired_applications=hired,
        hire_rate_percent=round(100 * hired / closed, 1) if closed else None,
        top_skills=top_skills,
        published_courses=published_courses,
        active_enrollments=active_enrollments,
        course_completions=course_completions,
    )
