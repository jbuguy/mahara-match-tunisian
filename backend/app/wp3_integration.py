import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.matching import MatchResult as StoredMatchResult, SkillGap
from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import GapType, OfferStatus, RequirementLevel
from mahara_data.schemas.matching import RankedMatches, Roadmap

WP3_ROOT = Path(__file__).resolve().parents[2] / "skill-matching-wp3"


def _load_wp3_module(module_name: str):
    package_name = f"mahara_wp3_{module_name}"
    if package_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(package_name, WP3_ROOT / f"{module_name}.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load WP3 module: {module_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = module
        spec.loader.exec_module(module)
    return sys.modules[package_name]


_scoring = _load_wp3_module("scoring")


def _scoring_profile(candidate_id: UUID | str, profile: dict[str, Any]) -> dict[str, Any]:
    governorate = profile.get("governorate") or {}
    return {
        "candidate_id": str(candidate_id),
        "years_experience": profile.get("years_experience") or 0,
        "location": {"governorate_code": governorate.get("code")},
        "mobility": {"governorates": []},
        "skills": [
            {
                "skill_code": skill["code"],
                "label_raw": skill.get("label_fr", ""),
                "skill_type": skill.get("skill_type"),
                "level": skill["level"],
            }
            for skill in profile.get("skills", [])
        ],
    }


def _published_offers(db: Session) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    offers = (
        db.query(JobOffer)
        .filter(
            JobOffer.status == OfferStatus.PUBLISHED,
            or_(JobOffer.expires_at.is_(None), JobOffer.expires_at > now),
        )
        .all()
    )
    result = []
    for offer in offers:
        skills = (
            db.query(JobOfferSkill, Skill)
            .join(Skill, Skill.id == JobOfferSkill.skill_id)
            .filter(JobOfferSkill.job_offer_id == offer.id)
            .all()
        )
        result.append(
            {
                "job_offer_id": str(offer.id),
                "min_years_experience": float(offer.min_years_experience or 0),
                "location": {"governorate_code": offer.governorate_code},
                "skills": [
                    {
                        "skill_code": skill.code,
                        "label_raw": skill.label_fr,
                        "skill_type": skill.skill_type.value,
                        "requirement": association.requirement.value,
                        "min_level": association.min_level,
                    }
                    for association, skill in skills
                ],
            }
        )
    return result


def _persist_matches(db: Session, result: dict[str, Any]) -> None:
    candidate_id = UUID(result["subject_id"])
    db.query(StoredMatchResult).filter(StoredMatchResult.candidate_id == candidate_id).update(
        {"is_current": False}, synchronize_session=False
    )
    skill_codes = {
        gap["skill_code"]
        for item in result["items"]
        for gap in item["gaps"]
    }
    skills_by_code = {
        skill.code: skill
        for skill in db.query(Skill).filter(Skill.code.in_(skill_codes)).all()
    } if skill_codes else {}

    for item in result["items"]:
        offer_id = UUID(item["job_offer_id"])
        stored = (
            db.query(StoredMatchResult)
            .filter(
                StoredMatchResult.candidate_id == candidate_id,
                StoredMatchResult.job_offer_id == offer_id,
                StoredMatchResult.model_version == item["model_version"],
            )
            .first()
        )
        if stored is None:
            stored = StoredMatchResult(
                candidate_id=candidate_id,
                job_offer_id=offer_id,
                model_version=item["model_version"],
                weights=item["weights"],
            )
            db.add(stored)

        breakdown = item["breakdown"]
        stored.score_global = item["score_global"]
        stored.score_hard_skills = breakdown["hard_skills"]
        stored.score_experience = breakdown["experience"]
        stored.score_soft_skills = breakdown["soft_skills"]
        stored.score_location = breakdown["location"]
        stored.weights = item["weights"]
        stored.computed_at = datetime.fromisoformat(item["computed_at"])
        stored.is_current = True
        db.flush()

        db.query(SkillGap).filter(SkillGap.match_result_id == stored.id).delete(synchronize_session=False)
        for gap in item["gaps"]:
            skill = skills_by_code.get(gap["skill_code"])
            if skill is None:
                raise RuntimeError(f"WP1 offer references unknown skill code: {gap['skill_code']}")
            db.add(
                SkillGap(
                    match_result_id=stored.id,
                    skill_id=skill.id,
                    gap_type=GapType(gap["gap_type"]),
                    requirement=RequirementLevel(gap["requirement"]),
                    required_level=gap["required_level"],
                    current_level=gap.get("current_level"),
                )
            )
        item["match_id"] = str(stored.id)
    db.commit()


def create_wp3_router(get_db: Any, get_current_user: Any, profile_reader: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/me/matches", tags=["wp3-matching"])

    def candidate_profile(db: Session, user: Any) -> dict[str, Any]:
        snapshot = profile_reader(db, user.id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="profile not found")
        candidate_id, profile = snapshot
        return _scoring_profile(candidate_id, profile)

    @router.get("")
    def get_matches(
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        profile = candidate_profile(db, user)
        result = _scoring.classer_offres(profile, _published_offers(db))
        _persist_matches(db, result)
        return RankedMatches.model_validate(result).model_dump(mode="json")

    @router.get("/{job_offer_id}/roadmap")
    def get_roadmap(
        job_offer_id: str,
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        profile = candidate_profile(db, user)
        try:
            offer_uuid = UUID(job_offer_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Offer not found") from None
        offer = db.get(JobOffer, offer_uuid)
        if offer is None or offer.status is not OfferStatus.PUBLISHED:
            raise HTTPException(status_code=404, detail="Offer not found")

        scoring_offer = next(
            (item for item in _published_offers(db) if item["job_offer_id"] == str(offer_uuid)),
            None,
        )
        if scoring_offer is None:
            raise HTTPException(status_code=404, detail="Offer not found")
        roadmap = _scoring.generer_roadmap(profile, scoring_offer)
        if roadmap is None:
            return {"status": "no_gap", "message": "The candidate already meets this offer's skill requirements."}
        return Roadmap.model_validate(roadmap).model_dump(mode="json")

    return router