"""Candidate offer feed assembly."""

import uuid

from sqlalchemy.orm import Session

from .applications import ApplicationWorkflowError
from ..repositories import applications as application_repository
from ..repositories import offers as offer_repository


def list_candidate_offers(db: Session, *, user_id: uuid.UUID) -> list[dict]:
    candidate = application_repository.get_candidate_for_user(db, user_id)
    if candidate is None:
        raise ApplicationWorkflowError(404, "Candidate profile not found")

    rows = offer_repository.list_published_offers(db, candidate.id)
    offer_ids = [offer.id for offer, _match, _application in rows]
    skills_by_offer: dict[uuid.UUID, list[dict]] = {offer_id: [] for offer_id in offer_ids}
    for link, skill in offer_repository.list_offer_skills(db, offer_ids):
        skills_by_offer[link.job_offer_id].append(
            {
                "code": skill.code,
                "label_fr": skill.label_fr,
                "requirement": link.requirement.value,
                "min_level": link.min_level,
            }
        )

    return [
        {
            "offer_id": str(offer.id),
            "title": offer.title,
            "description": offer.description_normalized or offer.description_raw,
            "contract_type": offer.contract_type.value,
            "work_mode": offer.work_mode.value,
            "governorate_code": offer.governorate_code,
            "delegation": offer.delegation,
            "positions_count": offer.positions_count,
            "min_years_experience": float(offer.min_years_experience or 0),
            "education_level_min": offer.education_level_min.value if offer.education_level_min else None,
            "salary_min_tnd": float(offer.salary_min_tnd) if offer.salary_min_tnd is not None else None,
            "salary_max_tnd": float(offer.salary_max_tnd) if offer.salary_max_tnd is not None else None,
            "published_at": offer.published_at.isoformat() if offer.published_at else None,
            "match_score": float(match.score_global) if match is not None else None,
            "application_status": application.status.value if application is not None else None,
            "skills": skills_by_offer[offer.id],
        }
        for offer, match, application in rows
    ]
