"""Published-offer queries for the candidate journey."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from mahara_data.db.models.employers import Application, JobOffer, JobOfferSkill
from mahara_data.db.models.matching import MatchResult
from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import OfferStatus


def list_published_offers(db: Session, candidate_id: UUID):
    now = datetime.now(timezone.utc)
    return (
        db.query(JobOffer, MatchResult, Application)
        .outerjoin(
            MatchResult,
            (MatchResult.job_offer_id == JobOffer.id)
            & (MatchResult.candidate_id == candidate_id)
            & MatchResult.is_current.is_(True),
        )
        .filter(
            JobOffer.status == OfferStatus.PUBLISHED,
            or_(JobOffer.expires_at.is_(None), JobOffer.expires_at > now),
        )
        .outerjoin(Application, (Application.job_offer_id == JobOffer.id) & (Application.candidate_id == candidate_id))
        .order_by(MatchResult.score_global.desc().nullslast(), JobOffer.published_at.desc())
        .all()
    )


def list_offer_skills(db: Session, offer_ids: list[UUID]):
    if not offer_ids:
        return []
    return (
        db.query(JobOfferSkill, Skill)
        .join(Skill, Skill.id == JobOfferSkill.skill_id)
        .filter(JobOfferSkill.job_offer_id.in_(offer_ids))
        .order_by(JobOfferSkill.job_offer_id, JobOfferSkill.requirement, Skill.label_fr)
        .all()
    )
