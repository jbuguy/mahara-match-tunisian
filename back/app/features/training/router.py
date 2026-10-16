"""Training provider self-service catalog endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Skill
from mahara_data.db.models.training import TrainingCourse, TrainingCourseSkill, TrainingProvider
from mahara_data.enums import CourseModality
from mahara_data.repositories.taxonomy import get_validated_skills_by_codes


class CourseSkillInput(BaseModel):
    skill_code: str = Field(min_length=1, max_length=32)
    target_level: int = Field(ge=1, le=4)


class CourseInput(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    modality: CourseModality
    duration_hours: int | None = Field(default=None, ge=1, le=5000)
    cost_tnd: float | None = Field(default=None, ge=0)
    governorate_code: str | None = Field(default=None, max_length=8)
    language: str = Field(default="fr", max_length=8)
    certification_name: str | None = Field(default=None, max_length=200)
    external_ref: str | None = Field(default=None, max_length=64)
    skills: list[CourseSkillInput] = Field(min_length=1, max_length=30)


def create_training_provider_router(get_db: Any, get_current_user: Any) -> APIRouter:
    router = APIRouter(prefix="/api/v1/training-provider", tags=["training-provider"])

    def current_provider(db: Session, user: Any) -> TrainingProvider:
        roles = {str(role).strip().lower() for role in (user.roles or [])}
        if "training_provider" not in roles:
            raise HTTPException(status_code=403, detail="Training provider access is required")
        provider = db.query(TrainingProvider).filter(TrainingProvider.user_id == user.id).one_or_none()
        if provider is None:
            raise HTTPException(status_code=404, detail="No training center is linked to this account")
        return provider

    def course_payload(db: Session, course: TrainingCourse) -> dict[str, Any]:
        rows = db.query(TrainingCourseSkill, Skill).join(Skill, Skill.id == TrainingCourseSkill.skill_id).filter(
            TrainingCourseSkill.training_course_id == course.id
        ).order_by(Skill.label_fr).all()
        return {
            "course_id": str(course.id), "title": course.title, "description": course.description,
            "modality": course.modality.value, "duration_hours": course.duration_hours,
            "cost_tnd": float(course.cost_tnd) if course.cost_tnd is not None else None,
            "governorate_code": course.governorate_code, "language": course.language,
            "certification_name": course.certification_name, "external_ref": course.external_ref,
            "is_active": course.is_active,
            "skills": [{"code": skill.code, "label_fr": skill.label_fr, "target_level": link.target_level} for link, skill in rows],
        }

    def replace_course_skills(db: Session, course: TrainingCourse, skills: list[CourseSkillInput]) -> None:
        codes = [skill.skill_code for skill in skills]
        if len(set(codes)) != len(codes):
            raise HTTPException(status_code=422, detail="A skill can only be added once")
        validated = {skill.code: skill for skill in get_validated_skills_by_codes(db, codes)}
        if set(validated) != set(codes):
            raise HTTPException(status_code=422, detail="Choose skills from the validated taxonomy")
        db.query(TrainingCourseSkill).filter(TrainingCourseSkill.training_course_id == course.id).delete()
        for item in skills:
            db.add(TrainingCourseSkill(training_course_id=course.id, skill_id=validated[item.skill_code].id, target_level=item.target_level))

    @router.get("/me")
    def get_provider(
        db: Annotated[Session, Depends(get_db)], user: Annotated[Any, Depends(get_current_user)],
    ):
        provider = current_provider(db, user)
        region = db.get(Governorate, provider.governorate_code) if provider.governorate_code else None
        return {"provider_id": str(provider.id), "name": provider.name, "provider_type": provider.provider_type,
                "accreditation_ref": provider.accreditation_ref, "governorate": region.name_fr if region else None,
                "website": provider.website}

    @router.get("/courses")
    def list_courses(
        db: Annotated[Session, Depends(get_db)], user: Annotated[Any, Depends(get_current_user)],
    ):
        provider = current_provider(db, user)
        courses = db.query(TrainingCourse).filter(TrainingCourse.provider_id == provider.id).order_by(TrainingCourse.created_at.desc()).all()
        return [course_payload(db, course) for course in courses]

    @router.post("/courses", status_code=status.HTTP_201_CREATED)
    def create_course(
        body: CourseInput, db: Annotated[Session, Depends(get_db)], user: Annotated[Any, Depends(get_current_user)],
    ):
        provider = current_provider(db, user)
        if body.governorate_code and db.get(Governorate, body.governorate_code) is None:
            raise HTTPException(status_code=422, detail="Unknown governorate")
        course = TrainingCourse(provider_id=provider.id, title=body.title.strip(), description=body.description,
            modality=body.modality, duration_hours=body.duration_hours, cost_tnd=body.cost_tnd,
            governorate_code=body.governorate_code, language=body.language, certification_name=body.certification_name,
            external_ref=body.external_ref, is_active=True)
        db.add(course); db.flush()
        replace_course_skills(db, course, body.skills)
        db.commit(); db.refresh(course)
        return course_payload(db, course)

    @router.patch("/courses/{course_id}/availability")
    def set_course_availability(
        course_id: uuid.UUID, is_active: bool, db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        provider = current_provider(db, user)
        course = db.query(TrainingCourse).filter(TrainingCourse.id == course_id, TrainingCourse.provider_id == provider.id).one_or_none()
        if course is None:
            raise HTTPException(status_code=404, detail="Course not found")
        course.is_active = is_active
        db.commit(); db.refresh(course)
        return course_payload(db, course)

    return router
