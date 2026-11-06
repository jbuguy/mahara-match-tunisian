"""Candidate-owned learning roadmaps and labor-market career suggestions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.matching import Roadmap, RoadmapItem
from mahara_data.db.models.taxonomy import Occupation, OccupationSkill, Skill, SkillRelation
from mahara_data.db.models.training import TrainingCourse, TrainingCourseSkill, TrainingProvider
from mahara_data.enums import (
    OfferStatus,
    RequirementLevel,
    RoadmapItemStatus,
    RoadmapStatus,
    TaxonomyStatus,
)
from mahara_data.schemas.matching import Roadmap as RoadmapContract

from . import scoring

MODEL_VERSION = "career-roadmap-1.0"
CAREER_WINDOW_DAYS = 90
MIN_POSITIONS_FOR_TREND = 3
_RELATION_CREDIT = {"related": 0.4, "broader": 0.55, "equivalent": 1.0}


class RoadmapCreateIn(BaseModel):
    target_job_offer_id: uuid.UUID | None = None
    target_occupation_code: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def exactly_one_target(self) -> "RoadmapCreateIn":
        if (self.target_job_offer_id is None) == (self.target_occupation_code is None):
            raise ValueError("Provide exactly one job offer or occupation target")
        return self


class RoadmapItemUpdateIn(BaseModel):
    status: RoadmapItemStatus


class RoadmapStatusUpdateIn(BaseModel):
    status: Literal["active", "abandoned"]


def _candidate_skills(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item.get("skill_code") or item.get("code"): item
        for item in profile.get("skills", [])
        if item.get("skill_code") or item.get("code")
    }


def _market_status(current_positions: int, previous_positions: int) -> str:
    if current_positions < MIN_POSITIONS_FOR_TREND or previous_positions < MIN_POSITIONS_FOR_TREND:
        return "insufficient_data"
    return "increasing" if current_positions > previous_positions else "stable_or_declining"


def _market_signal(
    db: Session,
    occupation_id: uuid.UUID,
    governorate_code: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=CAREER_WINDOW_DAYS)
    previous_start = current_start - timedelta(days=CAREER_WINDOW_DAYS)
    current_positions = func.sum(
        case((JobOffer.published_at >= current_start, JobOffer.positions_count), else_=0)
    )
    previous_positions = func.sum(
        case((JobOffer.published_at < current_start, JobOffer.positions_count), else_=0)
    )
    query = (
        select(current_positions, previous_positions, func.max(JobOffer.published_at))
        .where(
            JobOffer.occupation_id == occupation_id,
            JobOffer.status == OfferStatus.PUBLISHED,
            JobOffer.published_at >= previous_start,
            JobOffer.published_at < now,
        )
    )
    if governorate_code:
        query = query.where(JobOffer.governorate_code == governorate_code)
    recent, previous, latest = db.execute(query).one()
    recent = int(recent or 0)
    previous = int(previous or 0)
    change = round((recent - previous) * 100 / previous, 1) if previous else None
    return {
        "status": _market_status(recent, previous),
        "source": "Published Mahara Match job offers; observed posting activity, not a forecast",
        "current_period_start": current_start.date().isoformat(),
        "current_period_end": now.date().isoformat(),
        "previous_period_start": previous_start.date().isoformat(),
        "previous_period_end": (current_start - timedelta(days=1)).date().isoformat(),
        "current_positions": recent,
        "previous_positions": previous,
        "change_percent": change,
        "latest_offer_at": latest.isoformat() if latest else None,
        "governorate_code": governorate_code,
        "minimum_positions_per_period": MIN_POSITIONS_FOR_TREND,
    }


def _course_recommendations(
    db: Session,
    required_levels: dict[uuid.UUID, int],
) -> dict[uuid.UUID, list[dict[str, Any]]]:
    if not required_levels:
        return {}
    rows = db.execute(
        select(TrainingCourseSkill, TrainingCourse, TrainingProvider)
        .join(TrainingCourse, TrainingCourse.id == TrainingCourseSkill.training_course_id)
        .join(TrainingProvider, TrainingProvider.id == TrainingCourse.provider_id)
        .where(
            TrainingCourseSkill.skill_id.in_(required_levels),
            TrainingCourse.is_active.is_(True),
        )
        .order_by(
            TrainingCourse.cost_tnd.asc().nulls_last(),
            TrainingCourse.duration_hours.asc().nulls_last(),
            TrainingCourse.title,
            TrainingProvider.name,
        )
    ).all()
    courses: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for link, course, provider in rows:
        if link.target_level < required_levels[link.skill_id]:
            continue
        bucket = courses.setdefault(link.skill_id, [])
        if len(bucket) >= 3:
            continue
        bucket.append(
            {
                "course_id": str(course.id),
                "title": course.title,
                "provider_name": provider.name,
                "target_level": link.target_level,
                "description": course.description,
                "modality": course.modality.value,
                "duration_hours": course.duration_hours,
                "cost_tnd": float(course.cost_tnd) if course.cost_tnd is not None else None,
                "governorate_code": course.governorate_code,
                "language": course.language,
                "catalog_status": "active",
            }
        )
    return courses


def _transferable_skills(
    db: Session,
    candidate_codes: set[str],
    target_codes: set[str],
) -> dict[str, list[str]]:
    if not candidate_codes or not target_codes:
        return {}
    source = aliased(Skill)
    target = aliased(Skill)
    rows = db.execute(
        select(source.code, target.code, SkillRelation.relation_type)
        .join(SkillRelation, SkillRelation.source_skill_id == source.id)
        .join(target, SkillRelation.target_skill_id == target.id)
        .where(
            source.code.in_(candidate_codes),
            target.code.in_(target_codes),
            source.status == TaxonomyStatus.VALIDATED,
            target.status == TaxonomyStatus.VALIDATED,
        )
    ).all()
    result: dict[str, list[str]] = {}
    for source_code, target_code, relation_type in rows:
        relation = relation_type.value if hasattr(relation_type, "value") else str(relation_type)
        if relation in _RELATION_CREDIT:
            result.setdefault(target_code, []).append(source_code)
    return result


def _serialize_roadmap(
    db: Session,
    roadmap: Roadmap,
    profile: dict[str, Any],
) -> dict[str, Any]:
    occupation = db.get(Occupation, roadmap.target_occupation_id) if roadmap.target_occupation_id else None
    offer = db.get(JobOffer, roadmap.target_job_offer_id) if roadmap.target_job_offer_id else None
    items = db.execute(
        select(RoadmapItem, Skill)
        .join(Skill, Skill.id == RoadmapItem.skill_id)
        .where(RoadmapItem.roadmap_id == roadmap.id)
        .order_by(RoadmapItem.position)
    ).all()
    candidate_skills = _candidate_skills(profile)
    skill_codes = {skill.code for _, skill in items}
    transfer_map = _transferable_skills(db, set(candidate_skills), skill_codes)
    transfer_codes = {code for codes in transfer_map.values() for code in codes}
    transfer_labels = {
        skill.code: skill.label_fr
        for skill in db.query(Skill).filter(Skill.code.in_(transfer_codes))
    } if transfer_codes else {}
    courses = _course_recommendations(
        db,
        {skill.id: item.required_level for item, skill in items},
    )
    steps = []
    for item, skill in items:
        current = candidate_skills.get(skill.code)
        current_level = current.get("level") if current else None
        skill_courses = courses.get(skill.id, [])
        if item.training_course_id:
            skill_courses.sort(key=lambda course: course["course_id"] != str(item.training_course_id))
        steps.append(
            {
                "position": item.position,
                "skill_code": skill.code,
                "skill_label": skill.label_fr,
                "required_level": item.required_level,
                "current_level": current_level,
                "gap_type": "missing" if current_level is None else "insufficient_level",
                "transferable_skill_codes": sorted(transfer_map.get(skill.code, [])),
                "transferable_skills": [
                    {"skill_code": code, "label": transfer_labels.get(code, code)}
                    for code in sorted(transfer_map.get(skill.code, []))
                ],
                "training_course_id": str(item.training_course_id) if item.training_course_id else None,
                "courses": skill_courses,
                "learning_action": (
                    f"Build evidence in {skill.label_fr} with a small practical task, then ask an experienced person for feedback."
                ),
                "status": item.status.value,
            }
        )
    signal = None
    if occupation:
        governorate_code = (profile.get("location") or {}).get("governorate_code")
        signal = _market_signal(db, occupation.id, governorate_code)
    payload = {
        "roadmap_id": str(roadmap.id),
        "candidate_id": str(roadmap.candidate_id),
        "target_job_offer_id": str(roadmap.target_job_offer_id) if roadmap.target_job_offer_id else None,
        "target_job_title": offer.title if offer else None,
        "target_occupation_code": occupation.code if occupation else None,
        "target_occupation_title": occupation.title_fr if occupation else None,
        "market_signal": signal,
        "status": roadmap.status.value,
        "progress_pct": roadmap.progress_pct,
        "steps": steps,
        "model_version": roadmap.model_version,
    }
    return RoadmapContract.model_validate(payload).model_dump(mode="json")


def _find_existing(
    db: Session,
    candidate_id: uuid.UUID,
    offer_id: uuid.UUID | None,
    occupation_id: uuid.UUID | None,
) -> Roadmap | None:
    query = db.query(Roadmap).filter(
        Roadmap.candidate_id == candidate_id,
        Roadmap.status != RoadmapStatus.ABANDONED,
    )
    if offer_id:
        query = query.filter(Roadmap.target_job_offer_id == offer_id)
    else:
        query = query.filter(Roadmap.target_occupation_id == occupation_id)
    return query.order_by(Roadmap.created_at.desc()).first()


def _save_roadmap(
    db: Session,
    candidate_id: uuid.UUID,
    profile: dict[str, Any],
    gaps: list[dict[str, Any]],
    *,
    offer_id: uuid.UUID | None = None,
    occupation_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    existing = _find_existing(db, candidate_id, offer_id, occupation_id)
    if existing:
        return _serialize_roadmap(db, existing, profile)
    if not gaps:
        return {
            "status": "no_gap",
            "message": "Your current profile meets the validated skill requirements for this target.",
        }

    skill_codes = [item["skill_code"] for item in gaps]
    skills = {
        skill.code: skill
        for skill in db.query(Skill).filter(
            Skill.code.in_(skill_codes),
            Skill.status == TaxonomyStatus.VALIDATED,
        )
    }
    if set(skills) != set(skill_codes):
        raise HTTPException(status_code=409, detail="A target skill is no longer available in the validated taxonomy")

    roadmap = Roadmap(
        candidate_id=candidate_id,
        target_job_offer_id=offer_id,
        target_occupation_id=occupation_id,
        status=RoadmapStatus.ACTIVE,
        progress_pct=0,
        model_version=MODEL_VERSION,
    )
    db.add(roadmap)
    db.flush()
    recommendations = _course_recommendations(
        db,
        {skills[item["skill_code"]].id: item["required_level"] for item in gaps},
    )
    for position, gap in enumerate(gaps, start=1):
        skill = skills[gap["skill_code"]]
        course = recommendations.get(skill.id, [])
        db.add(
            RoadmapItem(
                roadmap_id=roadmap.id,
                skill_id=skill.id,
                training_course_id=uuid.UUID(course[0]["course_id"]) if course else None,
                position=position,
                required_level=gap["required_level"],
                status=RoadmapItemStatus.TODO,
            )
        )
    db.commit()
    db.refresh(roadmap)
    return _serialize_roadmap(db, roadmap, profile)


def create_or_get_offer_roadmap(
    db: Session,
    profile: dict[str, Any],
    offer_id: uuid.UUID,
) -> dict[str, Any]:
    offer = db.get(JobOffer, offer_id)
    now = datetime.now(timezone.utc)
    if (
        offer is None
        or offer.status != OfferStatus.PUBLISHED
        or (offer.expires_at is not None and offer.expires_at <= now)
    ):
        raise HTTPException(status_code=404, detail="Offer not found")
    skill_rows = db.execute(
        select(JobOfferSkill, Skill)
        .join(Skill, Skill.id == JobOfferSkill.skill_id)
        .where(
            JobOfferSkill.job_offer_id == offer.id,
            Skill.status == TaxonomyStatus.VALIDATED,
        )
    ).all()
    scoring_offer = {
        "job_offer_id": str(offer.id),
        "skills": [
            {
                "skill_code": skill.code,
                "label_raw": skill.label_fr,
                "requirement": link.requirement.value,
                "min_level": link.min_level,
            }
            for link, skill in skill_rows
        ],
    }
    candidate_id = uuid.UUID(str(profile["candidate_id"]))
    gaps = scoring.generer_roadmap(profile, scoring_offer)
    if gaps is None:
        return _save_roadmap(db, candidate_id, profile, [], offer_id=offer.id)
    return _save_roadmap(
        db,
        candidate_id,
        profile,
        [
            {
                "skill_code": step.get("skill_code"),
                "required_level": next(
                    row[0].min_level for row in skill_rows if row[1].code == step.get("skill_code")
                ),
            }
            for step in gaps["steps"]
        ],
        offer_id=offer.id,
    )


def create_roadmap_router(
    get_db: Any,
    get_current_user: Any,
    profile_reader: Callable[..., Any],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/me/roadmaps", tags=["career-roadmaps"])

    def candidate_context(db: Session, user: Any) -> tuple[uuid.UUID, dict[str, Any]]:
        snapshot = profile_reader(db, user.id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="profile not found")
        candidate_id, original = snapshot
        profile = {
            "candidate_id": str(candidate_id),
            "location": {"governorate_code": (original.get("governorate") or {}).get("code")},
            "skills": [
                {
                    "skill_code": item.get("skill_code") or item.get("code"),
                    "label_fr": item.get("label_fr") or item.get("label"),
                    "level": item["level"],
                }
                for item in original.get("skills", [])
                if item.get("skill_code") or item.get("code")
            ],
        }
        return uuid.UUID(str(candidate_id)), profile

    @router.get("/career-options")
    def career_options(
        limit: int = Query(default=12, ge=1, le=50),
        db: Session = Depends(get_db),
        user: Any = Depends(get_current_user),
    ) -> dict[str, Any]:
        _candidate_id, profile = candidate_context(db, user)
        candidate_skills = _candidate_skills(profile)
        candidate_codes = set(candidate_skills)
        governorate_code = (profile.get("location") or {}).get("governorate_code")
        occupations = db.execute(
            select(Occupation)
            .where(Occupation.status == TaxonomyStatus.VALIDATED)
            .order_by(Occupation.title_fr)
        ).scalars().all()
        if not occupations:
            return {"items": [], "market_method": "No validated occupations are available."}

        occupation_ids = [occupation.id for occupation in occupations]
        skill_rows = db.execute(
            select(OccupationSkill, Skill, Occupation.id)
            .join(Skill, Skill.id == OccupationSkill.skill_id)
            .join(Occupation, Occupation.id == OccupationSkill.occupation_id)
            .where(
                Occupation.id.in_(occupation_ids),
                Skill.status == TaxonomyStatus.VALIDATED,
            )
        ).all()
        skills_by_occupation: dict[uuid.UUID, list[tuple[OccupationSkill, Skill]]] = {}
        target_codes = set()
        for requirement, skill, occupation_id in skill_rows:
            skills_by_occupation.setdefault(occupation_id, []).append((requirement, skill))
            target_codes.add(skill.code)
        transfer_map = _transferable_skills(db, candidate_codes, target_codes)
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=CAREER_WINDOW_DAYS)
        previous_start = current_start - timedelta(days=CAREER_WINDOW_DAYS)
        current_positions = func.sum(
            case((JobOffer.published_at >= current_start, JobOffer.positions_count), else_=0)
        )
        previous_positions = func.sum(
            case((JobOffer.published_at < current_start, JobOffer.positions_count), else_=0)
        )
        demand = {
            row.occupation_id: (int(row.current or 0), int(row.previous or 0), row.latest)
            for row in db.execute(
                select(
                    JobOffer.occupation_id.label("occupation_id"),
                    current_positions.label("current"),
                    previous_positions.label("previous"),
                    func.max(JobOffer.published_at).label("latest"),
                )
                .where(
                    JobOffer.status == OfferStatus.PUBLISHED,
                    JobOffer.occupation_id.in_(occupation_ids),
                    JobOffer.published_at >= previous_start,
                    JobOffer.published_at < now,
                    *(
                        [JobOffer.governorate_code == governorate_code]
                        if governorate_code
                        else []
                    ),
                )
                .group_by(JobOffer.occupation_id)
            )
        }

        items = []
        for occupation in occupations:
            requirements = skills_by_occupation.get(occupation.id, [])
            if not requirements:
                continue
            matched = []
            matched_labels = []
            gaps = []
            transferable = []
            for requirement, skill in requirements:
                candidate_skill = candidate_skills.get(skill.code)
                if candidate_skill and candidate_skill.get("level", 0) >= 2:
                    matched.append(skill.code)
                    matched_labels.append(skill.label_fr)
                    continue
                related = sorted(transfer_map.get(skill.code, []))
                if related:
                    transferable.extend(related)
                gaps.append(
                    {
                        "skill_code": skill.code,
                        "skill_label": skill.label_fr,
                        "current_level": candidate_skill.get("level") if candidate_skill else None,
                        "required_level": 2,
                        "requirement": requirement.requirement.value,
                        "transferable_skill_codes": related,
                    }
                )
            current, previous, latest = demand.get(occupation.id, (0, 0, None))
            change = round((current - previous) * 100 / previous, 1) if previous else None
            trend = _market_status(current, previous)
            items.append(
                {
                    "occupation_code": occupation.code,
                    "title": occupation.title_fr,
                    "description": occupation.description,
                    "skill_count": len(requirements),
                    "matched_skill_codes": sorted(matched),
                    "matched_skill_labels": sorted(set(matched_labels)),
                    "transferable_skill_codes": sorted(set(transferable)),
                    "transferable_skills": [
                        {
                            "skill_code": code,
                            "label": (candidate_skills.get(code) or {}).get("label_fr") or code,
                        }
                        for code in sorted(set(transferable))
                    ],
                    "gaps": gaps,
                    "market_signal": {
                        "status": trend,
                        "source": "Published Mahara Match job offers; observed posting activity, not a forecast",
                        "current_period_start": current_start.date().isoformat(),
                        "current_period_end": now.date().isoformat(),
                        "previous_period_start": previous_start.date().isoformat(),
                        "previous_period_end": (current_start - timedelta(days=1)).date().isoformat(),
                        "current_positions": current,
                        "previous_positions": previous,
                        "change_percent": change,
                        "latest_offer_at": latest.isoformat() if latest else None,
                        "governorate_code": governorate_code,
                        "minimum_positions_per_period": MIN_POSITIONS_FOR_TREND,
                    },
                }
            )
        items.sort(
            key=lambda item: (
                -len(item["matched_skill_codes"]),
                -len(item["transferable_skill_codes"]),
                item["market_signal"]["status"] != "increasing",
                -item["market_signal"]["current_positions"],
                item["title"].casefold(),
            )
        )
        return {
            "items": items[:limit],
            "market_method": (
                "Compares positions in published platform offers over two consecutive 90-day periods. "
                f"An increasing signal requires at least {MIN_POSITIONS_FOR_TREND} positions in each period; "
                "this is platform activity, not a forecast or a complete labor-market measure."
            ),
        }

    @router.get("")
    def list_roadmaps(
        db: Session = Depends(get_db),
        user: Any = Depends(get_current_user),
    ) -> list[dict[str, Any]]:
        candidate_id, profile = candidate_context(db, user)
        roadmaps = (
            db.query(Roadmap)
            .filter(Roadmap.candidate_id == candidate_id)
            .order_by(Roadmap.updated_at.desc())
            .all()
        )
        return [_serialize_roadmap(db, roadmap, profile) for roadmap in roadmaps]

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_roadmap(
        body: RoadmapCreateIn,
        response: Response,
        db: Session = Depends(get_db),
        user: Any = Depends(get_current_user),
    ) -> dict[str, Any]:
        candidate_id, profile = candidate_context(db, user)
        if body.target_job_offer_id:
            existing = _find_existing(db, candidate_id, body.target_job_offer_id, None)
            result = create_or_get_offer_roadmap(db, profile, body.target_job_offer_id)
            if existing or result.get("status") == "no_gap":
                response.status_code = status.HTTP_200_OK
            return result

        occupation = (
            db.query(Occupation)
            .filter(
                Occupation.code == body.target_occupation_code,
                Occupation.status == TaxonomyStatus.VALIDATED,
            )
            .one_or_none()
        )
        if occupation is None:
            raise HTTPException(status_code=404, detail="Validated occupation not found")
        requirements = db.execute(
            select(OccupationSkill, Skill)
            .join(Skill, Skill.id == OccupationSkill.skill_id)
            .where(
                OccupationSkill.occupation_id == occupation.id,
                Skill.status == TaxonomyStatus.VALIDATED,
            )
        ).all()
        candidate_skills = _candidate_skills(profile)
        gaps = []
        for requirement, skill in requirements:
            current = candidate_skills.get(skill.code)
            if current and current.get("level", 0) >= 2:
                continue
            gaps.append(
                {
                    "skill_code": skill.code,
                    "required_level": 2,
                    "requirement": requirement.requirement.value,
                }
            )
        gaps.sort(
            key=lambda item: (
                item["requirement"] != RequirementLevel.REQUIRED.value,
                candidate_skills.get(item["skill_code"], {}).get("level", 0),
                item["skill_code"],
            )
        )
        if not requirements:
            raise HTTPException(status_code=409, detail="This occupation has no validated skill requirements")
        existing = _find_existing(db, candidate_id, None, occupation.id)
        result = _save_roadmap(
            db,
            candidate_id,
            profile,
            gaps,
            occupation_id=occupation.id,
        )
        if existing or result.get("status") == "no_gap":
            response.status_code = status.HTTP_200_OK
        return result

    @router.get("/{roadmap_id}")
    def get_roadmap(
        roadmap_id: uuid.UUID,
        db: Session = Depends(get_db),
        user: Any = Depends(get_current_user),
    ) -> dict[str, Any]:
        candidate_id, profile = candidate_context(db, user)
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == roadmap_id,
            Roadmap.candidate_id == candidate_id,
        ).one_or_none()
        if roadmap is None:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        return _serialize_roadmap(db, roadmap, profile)

    @router.patch("/{roadmap_id}/steps/{position}")
    def update_step(
        roadmap_id: uuid.UUID,
        position: int,
        body: RoadmapItemUpdateIn,
        db: Session = Depends(get_db),
        user: Any = Depends(get_current_user),
    ) -> dict[str, Any]:
        candidate_id, profile = candidate_context(db, user)
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == roadmap_id,
            Roadmap.candidate_id == candidate_id,
        ).with_for_update().one_or_none()
        if roadmap is None:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        item = db.query(RoadmapItem).filter(
            RoadmapItem.roadmap_id == roadmap.id,
            RoadmapItem.position == position,
        ).one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="Roadmap step not found")
        item.status = body.status
        now = datetime.now(timezone.utc)
        if body.status == RoadmapItemStatus.IN_PROGRESS:
            item.started_at = item.started_at or now
            item.completed_at = None
        elif body.status == RoadmapItemStatus.DONE:
            item.started_at = item.started_at or now
            item.completed_at = now
        else:
            item.completed_at = None
        db.flush()
        items = db.query(RoadmapItem).filter(RoadmapItem.roadmap_id == roadmap.id).all()
        completed_count = sum(item.status == RoadmapItemStatus.DONE for item in items)
        roadmap.progress_pct = round(100 * completed_count / len(items)) if items else 0
        if completed_count == len(items):
            roadmap.status = RoadmapStatus.COMPLETED
        elif roadmap.status == RoadmapStatus.COMPLETED:
            roadmap.status = RoadmapStatus.ACTIVE
        db.commit()
        db.refresh(roadmap)
        return _serialize_roadmap(db, roadmap, profile)

    @router.patch("/{roadmap_id}/status")
    def update_roadmap_status(
        roadmap_id: uuid.UUID,
        body: RoadmapStatusUpdateIn,
        db: Session = Depends(get_db),
        user: Any = Depends(get_current_user),
    ) -> dict[str, Any]:
        candidate_id, profile = candidate_context(db, user)
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == roadmap_id,
            Roadmap.candidate_id == candidate_id,
        ).with_for_update().one_or_none()
        if roadmap is None:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        if body.status == RoadmapStatus.ACTIVE.value:
            items = db.query(RoadmapItem).filter(RoadmapItem.roadmap_id == roadmap.id).all()
            roadmap.status = (
                RoadmapStatus.COMPLETED
                if items and all(item.status == RoadmapItemStatus.DONE for item in items)
                else RoadmapStatus.ACTIVE
            )
        else:
            roadmap.status = RoadmapStatus.ABANDONED
        db.commit()
        db.refresh(roadmap)
        return _serialize_roadmap(db, roadmap, profile)

    return router
