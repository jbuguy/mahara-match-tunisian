"""Candidate profile: read it back as one object, save it as one transaction."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, nulls_last, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    CandidateDesiredOccupation,
    CandidateEducation,
    CandidateExperience,
    CandidatePii,
    CandidateSkill,
    Governorate,
    Occupation,
    Skill,
    User,
)
from app.schemas import (
    EducationOut,
    ExperienceOut,
    GovernorateOut,
    LanguageOut,
    ProfileIn,
    ProfileOccupationOut,
    ProfileOut,
    ProfileSkillOut,
)

CONSENT_VERSION = "1.0"


def get_profile(db: Session, user_id: uuid.UUID) -> ProfileOut | None:
    candidate = db.scalar(select(Candidate).where(Candidate.user_id == user_id))
    if candidate is None:
        return None
    pii = db.get(CandidatePii, candidate.id)
    governorate = db.get(Governorate, candidate.governorate_code) if candidate.governorate_code else None

    skills = db.execute(
        select(CandidateSkill, Skill)
        .join(Skill, Skill.id == CandidateSkill.skill_id)
        .where(CandidateSkill.candidate_id == candidate.id)
        .order_by(CandidateSkill.level.desc(), Skill.label_fr)
    ).all()
    experiences = db.scalars(
        select(CandidateExperience)
        .where(CandidateExperience.candidate_id == candidate.id)
        .order_by(nulls_last(CandidateExperience.start_date.desc()), CandidateExperience.job_title_raw)
    ).all()
    educations = db.scalars(
        select(CandidateEducation)
        .where(CandidateEducation.candidate_id == candidate.id)
        .order_by(nulls_last(CandidateEducation.graduation_year.desc()), CandidateEducation.field_of_study)
    ).all()
    occupations = db.execute(
        select(CandidateDesiredOccupation, Occupation)
        .join(Occupation, Occupation.id == CandidateDesiredOccupation.occupation_id)
        .where(CandidateDesiredOccupation.candidate_id == candidate.id)
        .order_by(nulls_last(CandidateDesiredOccupation.priority.asc()), Occupation.title_fr)
    ).all()

    return ProfileOut(
        full_name=pii.full_name if pii else None,
        email=pii.email if pii else None,
        phone=pii.phone if pii else None,
        onboarding_path=candidate.onboarding_path,
        literacy_level=candidate.literacy_level,
        governorate=GovernorateOut.model_validate(governorate) if governorate else None,
        education_level=candidate.education_level,
        years_experience=candidate.years_experience,
        languages=[LanguageOut(**language) for language in candidate.languages or []],
        summary=candidate.summary,
        available_from=candidate.available_from,
        consent_version=candidate.consent_version,
        consent_given_at=candidate.consent_given_at,
        skills=[
            ProfileSkillOut(
                code=skill.code,
                label_fr=skill.label_fr,
                skill_type=skill.skill_type,
                level=link.level,
                source=link.source,
                confidence=link.confidence,
            )
            for link, skill in skills
        ],
        experiences=[ExperienceOut.model_validate(row) for row in experiences],
        educations=[EducationOut.model_validate(row) for row in educations],
        desired_occupations=[
            ProfileOccupationOut(code=occupation.code, title_fr=occupation.title_fr, priority=link.priority)
            for link, occupation in occupations
        ],
    )


def _unknown_code(loc: list, code: str, what: str) -> dict:
    """Same shape as FastAPI's own 422 errors, so the form handles one format."""
    return {"type": "unknown_code", "loc": ["body", *loc], "msg": f"unknown {what} code", "input": code}


def _resolve_codes(db: Session, body: ProfileIn) -> tuple[dict[str, uuid.UUID], dict[str, uuid.UUID]]:
    """Map the request's skill and occupation codes to ids; 422 listing every unknown code."""
    skill_codes = [item.code for item in body.skills]
    occupation_codes = [item.code for item in body.desired_occupations]
    skill_ids: dict[str, uuid.UUID] = {}
    if skill_codes:
        skill_ids = dict(db.execute(
            select(Skill.code, Skill.id).where(Skill.code.in_(skill_codes), Skill.status == "validated")
        ).all())
    occupation_ids: dict[str, uuid.UUID] = {}
    if occupation_codes:
        occupation_ids = dict(db.execute(
            select(Occupation.code, Occupation.id).where(Occupation.code.in_(occupation_codes))
        ).all())

    errors = []
    if body.governorate_code and db.get(Governorate, body.governorate_code) is None:
        errors.append(_unknown_code(["governorate_code"], body.governorate_code, "governorate"))
    errors += [
        _unknown_code(["skills", i, "code"], code, "skill")
        for i, code in enumerate(skill_codes)
        if code not in skill_ids
    ]
    errors += [
        _unknown_code(["desired_occupations", i, "code"], code, "occupation")
        for i, code in enumerate(occupation_codes)
        if code not in occupation_ids
    ]
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=errors)
    return skill_ids, occupation_ids


def save_profile(db: Session, user: User, body: ProfileIn) -> ProfileOut:
    """Create or update the candidate, its PII, and replace skills, experiences, educations and desired jobs."""
    skill_ids, occupation_ids = _resolve_codes(db, body)
    try:
        candidate = db.scalar(select(Candidate).where(Candidate.user_id == user.id))
        if candidate is None:
            candidate = Candidate(
                id=uuid.uuid4(),
                user_id=user.id,
                onboarding_path="cv_upload" if body.from_cv else "derja_detailed",
                literacy_level=body.literacy_level or "literate",
            )
            db.add(candidate)
        else:
            # Keep how the profile was first created; a later CV import still marks it as cv_upload.
            if body.from_cv:
                candidate.onboarding_path = "cv_upload"
            if body.literacy_level:
                candidate.literacy_level = body.literacy_level
        if candidate.consent_given_at is None:
            candidate.consent_version = CONSENT_VERSION
            candidate.consent_given_at = datetime.now(UTC)

        candidate.governorate_code = body.governorate_code
        candidate.education_level = body.education_level
        candidate.years_experience = body.years_experience
        candidate.languages = [language.model_dump() for language in body.languages]
        candidate.summary = body.summary
        candidate.available_from = body.available_from
        db.flush()

        pii = db.get(CandidatePii, candidate.id) or CandidatePii(candidate_id=candidate.id)
        pii.full_name = body.full_name
        pii.email = body.email or user.email
        pii.phone = body.phone
        db.add(pii)

        for table in (CandidateSkill, CandidateExperience, CandidateEducation, CandidateDesiredOccupation):
            db.execute(delete(table).where(table.candidate_id == candidate.id))
        db.add_all(
            CandidateSkill(
                candidate_id=candidate.id,
                skill_id=skill_ids[item.code],
                level=item.level,
                source=item.source,
                confidence=item.confidence,
            )
            for item in body.skills
        )
        db.add_all(
            CandidateExperience(id=uuid.uuid4(), candidate_id=candidate.id, **item.model_dump())
            for item in body.experiences
        )
        db.add_all(
            CandidateEducation(id=uuid.uuid4(), candidate_id=candidate.id, **item.model_dump())
            for item in body.educations
        )
        db.add_all(
            CandidateDesiredOccupation(
                candidate_id=candidate.id,
                occupation_id=occupation_ids[item.code],
                priority=item.priority or position,
            )
            for position, item in enumerate(body.desired_occupations, start=1)
        )
        db.commit()
    except IntegrityError as exc:
        # Two first saves at once both tried to create the candidates row.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile changed, try again") from exc
    except Exception:
        db.rollback()
        raise

    profile = get_profile(db, user.id)
    assert profile is not None
    return profile
