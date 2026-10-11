"""Candidate profile: read it back as one object, save it as one transaction.

The database is far away (~200 ms per round trip), so both paths keep the number of statements low:
reading is a single query, saving batches what it can.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import literal_column, null, select, text, union_all
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import (
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
from ..schemas import ProfileIn, ProfileOut

CONSENT_VERSION = "1.0"

# The whole profile as one JSON object, in one round trip. Same shape and order as ProfileOut.
PROFILE_QUERY = text("""
select json_build_object(
    'full_name', p.full_name,
    'email', p.email,
    'phone', p.phone,
    'has_photo', p.photo is not null,
    'onboarding_path', c.onboarding_path,
    'literacy_level', c.literacy_level,
    'governorate', case when g.code is null then null
                   else json_build_object('code', g.code, 'name_fr', g.name_fr, 'name_ar', g.name_ar) end,
    'education_level', c.education_level,
    'years_experience', c.years_experience,
    'languages', c.languages,
    'summary', c.summary,
    'available_from', c.available_from,
    'consent_version', c.consent_version,
    'consent_given_at', c.consent_given_at,
    'skills', coalesce((
        select json_agg(json_build_object(
                   'code', s.code, 'label_fr', s.label_fr, 'skill_type', s.skill_type,
                   'level', cs.level, 'source', cs.source, 'confidence', cs.confidence)
               order by cs.level desc, s.label_fr)
        from candidate_skills cs join skills s on s.id = cs.skill_id
        where cs.candidate_id = c.id), '[]'),
    'experiences', coalesce((
        select json_agg(json_build_object(
                   'id', e.id, 'job_title_raw', e.job_title_raw, 'employer_name', e.employer_name,
                   'start_date', e.start_date, 'end_date', e.end_date,
                   'duration_months', e.duration_months, 'description', e.description)
               order by e.start_date desc nulls last, e.job_title_raw)
        from candidate_experiences e
        where e.candidate_id = c.id), '[]'),
    'educations', coalesce((
        select json_agg(json_build_object(
                   'id', d.id, 'level', d.level, 'field_of_study', d.field_of_study,
                   'institution', d.institution, 'graduation_year', d.graduation_year)
               order by d.graduation_year desc nulls last, d.field_of_study)
        from candidate_educations d
        where d.candidate_id = c.id), '[]'),
    'desired_occupations', coalesce((
        select json_agg(json_build_object('code', o.code, 'title_fr', o.title_fr, 'priority', link.priority)
               order by link.priority asc nulls last, o.title_fr)
        from candidate_desired_occupations link join occupations o on o.id = link.occupation_id
        where link.candidate_id = c.id), '[]')
)
from candidates c
left join candidate_pii p on p.candidate_id = c.id
left join governorates g on g.code = c.governorate_code
where c.user_id = :user_id
""")

# Clears the lists a save replaces, in one statement (data-modifying CTEs always run).
CLEAR_LISTS = text("""
with skills as (delete from candidate_skills where candidate_id = :id),
     experiences as (delete from candidate_experiences where candidate_id = :id),
     educations as (delete from candidate_educations where candidate_id = :id),
     occupations as (delete from candidate_desired_occupations where candidate_id = :id)
select 1
""")


def get_profile(db: Session, user_id: uuid.UUID) -> ProfileOut | None:
    data = db.scalar(PROFILE_QUERY, {"user_id": user_id})
    return ProfileOut.model_validate(data) if data is not None else None


def _unknown_code(loc: list, code: str, what: str) -> dict:
    """Same shape as FastAPI's own 422 errors, so the form handles one format."""
    return {"type": "unknown_code", "loc": ["body", *loc], "msg": f"unknown {what} code", "input": code}


def _resolve_codes(db: Session, body: ProfileIn) -> tuple[dict[str, uuid.UUID], dict[str, uuid.UUID]]:
    """Map the request's skill and occupation codes to ids (one query); 422 listing every unknown code."""
    skill_codes = [item.code for item in body.skills]
    occupation_codes = [item.code for item in body.desired_occupations]
    lookups = []
    if skill_codes:
        lookups.append(
            select(literal_column("'skill'").label("kind"), Skill.code, Skill.id)
            .where(Skill.code.in_(skill_codes), Skill.status == "validated")
        )
    if occupation_codes:
        lookups.append(
            select(literal_column("'occupation'"), Occupation.code, Occupation.id)
            .where(Occupation.code.in_(occupation_codes))
        )
    if body.governorate_code:
        lookups.append(
            select(literal_column("'governorate'"), Governorate.code, null().cast(UUID(as_uuid=True)))
            .where(Governorate.code == body.governorate_code)
        )
    found: dict[str, dict] = {"skill": {}, "occupation": {}, "governorate": {}}
    if lookups:
        for kind, code, id_ in db.execute(union_all(*lookups)).all():
            found[kind][code] = id_
    skill_ids, occupation_ids = found["skill"], found["occupation"]

    errors = []
    if body.governorate_code and body.governorate_code not in found["governorate"]:
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
        is_new = candidate is None
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

        # Upsert the identity row in one statement; the photo column is left as it is.
        identity = {"full_name": body.full_name, "email": body.email or user.email, "phone": body.phone}
        db.execute(
            insert(CandidatePii)
            .values(candidate_id=candidate.id, **identity)
            .on_conflict_do_update(index_elements=[CandidatePii.candidate_id], set_=identity)
        )

        if not is_new:
            db.execute(CLEAR_LISTS, {"id": candidate.id})
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
