import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mahara_data.db.models.candidates import Candidate, CandidateSkill
from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import OfferStatus
from mahara_data.schemas.market import SkillGapAggregate

# Rule E4 of the WP5 RBAC matrix: no ministry cell may describe fewer than 10 people.
K_ANONYMITY = 10


def _demand(
    db: Session, period_start: date, period_end: date, governorate_code: str | None
) -> dict[tuple[uuid.UUID, str | None], int]:
    """Published offers requiring each skill. Offers with no publication date are out."""
    stmt = (
        select(
            JobOfferSkill.skill_id,
            JobOffer.governorate_code,
            func.count(func.distinct(JobOffer.id)),
        )
        .join(JobOffer, JobOffer.id == JobOfferSkill.job_offer_id)
        .where(
            JobOffer.status == OfferStatus.PUBLISHED,
            JobOffer.published_at >= period_start,
            JobOffer.published_at < period_end + timedelta(days=1),
        )
        .group_by(JobOfferSkill.skill_id, JobOffer.governorate_code)
    )
    if governorate_code:
        stmt = stmt.where(JobOffer.governorate_code == governorate_code)

    return {(row[0], row[1]): row[2] for row in db.execute(stmt).all()}


def _supply(
    db: Session, governorate_code: str | None
) -> dict[tuple[uuid.UUID, str | None], int]:
    """Candidates holding each skill, as of now: a stock, not a flow."""
    stmt = (
        select(
            CandidateSkill.skill_id,
            Candidate.governorate_code,
            func.count(func.distinct(Candidate.id)),
        )
        .join(Candidate, Candidate.id == CandidateSkill.candidate_id)
        .group_by(CandidateSkill.skill_id, Candidate.governorate_code)
    )
    if governorate_code:
        stmt = stmt.where(Candidate.governorate_code == governorate_code)

    return {(row[0], row[1]): row[2] for row in db.execute(stmt).all()}


def _codes_for(db: Session, skill_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not skill_ids:
        return {}
    rows = db.execute(select(Skill.id, Skill.code).where(Skill.id.in_(skill_ids))).all()
    return {row[0]: row[1] for row in rows}


def skill_gap_map(
    db: Session,
    *,
    period_start: date,
    period_end: date,
    governorate_code: str | None = None,
    limit: int = 100,
) -> tuple[list[SkillGapAggregate], int]:
    """Cross demand and supply per skill and governorate, then apply the k threshold."""
    demand = _demand(db, period_start, period_end, governorate_code)
    supply = _supply(db, governorate_code)

    keys = set(demand) | set(supply)
    codes = _codes_for(db, {skill_id for skill_id, _ in keys})

    cells: list[SkillGapAggregate] = []
    suppressed = 0

    for skill_id, governorate in keys:
        people = supply.get((skill_id, governorate), 0)
        # Zero people reveals nobody, so it is published; 1 to 9 identifies them.
        if 0 < people < K_ANONYMITY:
            suppressed += 1
            continue

        code = codes.get(skill_id)
        if code is None:  # the skill was hard-deleted between the two queries
            continue

        offers = demand.get((skill_id, governorate), 0)
        cells.append(
            SkillGapAggregate(
                skill_code=code,
                governorate_code=governorate,
                demand_count=offers,
                supply_count=people,
                gap_ratio=round(offers / max(people, 1), 3),
                period_start=period_start,
                period_end=period_end,
            )
        )

    # Widest gap first, then the busiest, then alphabetically so the order is stable.
    cells.sort(key=lambda cell: (-cell.gap_ratio, -cell.demand_count, cell.skill_code))
    return cells[:limit], suppressed