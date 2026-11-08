import json
import re
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CandidateSkill,
    CourseSkill,
    OfferSkill,
    SkillAliasReview,
    SkillCatalogue,
)


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "skills_catalogue.json"


@lru_cache(maxsize=1)
def seed_catalogue() -> dict[str, list[str]]:
    with DATA_FILE.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def normalize_skill_key(value: str) -> str:
    value = value.strip().casefold()
    value = re.sub(r"[^a-z0-9\u00c0-\u024f]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonicalize_skills(session: Session, raw_skills: list[str], entity_type: str, entity_id: str) -> list[str]:
    aliases = {
        normalize_skill_key(alias): (skill["canonical_name_fr"], skill["id"])
        for skill in session.scalars(select(SkillCatalogue)).all()
        for alias in [skill.canonical_name_fr, skill.canonical_name_en, *skill.aliases]
    }
    recognized: dict[str, str] = {}
    unmatched: list[str] = []
    for raw in raw_skills:
        clean = str(raw).strip()
        if not clean:
            continue
        match = aliases.get(normalize_skill_key(clean))
        if match is None:
            unmatched.append(clean)
            continue
        canonical_name, skill_id = match
        recognized[skill_id] = canonical_name

        existing = session.scalar(
            select(SkillAliasReview).where(
                SkillAliasReview.entity_type == entity_type,
                SkillAliasReview.entity_id == entity_id,
                SkillAliasReview.raw_skill == clean,
            )
        )
        if existing is not None:
            session.delete(existing)

    for raw in dict.fromkeys(unmatched):
        existing = session.scalar(
            select(SkillAliasReview).where(
                SkillAliasReview.entity_type == entity_type,
                SkillAliasReview.entity_id == entity_id,
                SkillAliasReview.raw_skill == raw,
            )
        )
        if existing is None:
            session.add(SkillAliasReview(entity_type=entity_type, entity_id=entity_id, raw_skill=raw))
    return list(recognized.values())


def sync_candidate_skills(session: Session, user_id: str, raw_skills: list[str]) -> list[str]:
    session.query(CandidateSkill).filter(CandidateSkill.user_id == user_id).delete()
    session.flush()
    canonical_names = canonicalize_skills(session, raw_skills, "candidate", user_id)
    for name in canonical_names:
        skill = session.scalar(select(SkillCatalogue).where(SkillCatalogue.canonical_name_fr == name))
        if skill is not None:
            session.add(CandidateSkill(user_id=user_id, skill_id=skill.id))
    return canonical_names


def sync_offer_skills(session: Session, offer_id: str, required: list[str], preferred: list[str]) -> tuple[list[str], list[str]]:
    session.query(OfferSkill).filter(OfferSkill.offer_id == offer_id).delete()
    session.flush()
    for skill_type, raw_skills in (("required", required), ("preferred", preferred)):
        canonical_names = canonicalize_skills(session, raw_skills, f"offer:{skill_type}", offer_id)
        for raw in raw_skills:
            skill = resolve_skill(session, raw)
            if skill is not None and not session.get(OfferSkill, (offer_id, skill.id, skill_type)):
                session.add(OfferSkill(offer_id=offer_id, skill_id=skill.id, skill_type=skill_type))
    return (
        canonicalize_skills(session, required, "offer:required", offer_id),
        canonicalize_skills(session, preferred, "offer:preferred", offer_id),
    )


def sync_course_skills(session: Session, course_id: str, raw_skills: list[str]) -> list[str]:
    session.query(CourseSkill).filter(CourseSkill.course_id == course_id).delete()
    session.flush()
    canonicalize_skills(session, raw_skills, "course", course_id)
    for raw in raw_skills:
        skill = resolve_skill(session, raw)
        if skill is not None:
            session.add(CourseSkill(course_id=course_id, skill_id=skill.id))
    return canonicalize_skills(session, raw_skills, "course", course_id)


def resolve_skill(session: Session, raw: str):
    key = normalize_skill_key(raw)
    for skill in session.scalars(select(SkillCatalogue)).all():
        if key in {normalize_skill_key(value) for value in [skill.canonical_name_fr, skill.canonical_name_en, *skill.aliases]}:
            return skill
    return None


def recognised_skill_share(session: Session, entity_type: str | None = None) -> float:
    rows = session.scalars(select(SkillAliasReview)).all()
    review_count = sum(1 for row in rows if entity_type is None or row.entity_type == entity_type or row.entity_type.startswith(f"{entity_type}:"))
    if entity_type == "candidate":
        total = session.scalar(select(__import__("sqlalchemy").func.count()).select_from(CandidateSkill)) or 0
    elif entity_type == "course":
        total = session.scalar(select(__import__("sqlalchemy").func.count()).select_from(CourseSkill)) or 0
    elif entity_type in ("offer", "offer:required", "offer:preferred"):
        total = session.scalar(select(__import__("sqlalchemy").func.count()).select_from(OfferSkill)) or 0
    else:
        candidate_total = session.scalar(select(__import__("sqlalchemy").func.count()).select_from(CandidateSkill)) or 0
        course_total = session.scalar(select(__import__("sqlalchemy").func.count()).select_from(CourseSkill)) or 0
        offer_total = session.scalar(select(__import__("sqlalchemy").func.count()).select_from(OfferSkill)) or 0
        total = candidate_total + course_total + offer_total
    recognised = max(total, 1 if review_count == 0 else total)
    return recognised / (recognised + review_count) if recognised + review_count else 1.0
