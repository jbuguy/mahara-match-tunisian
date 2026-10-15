import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mahara_data.db.models.candidates import Candidate, CandidateDesiredOccupation, CandidateSkill
from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Occupation, Skill
from mahara_data.enums import OfferStatus
from mahara_data.schemas.market import SkillGapAggregate

from ..schemas import GovernorateDemandCell, OccupationTensionCell

# Rule E4 of the WP5 RBAC matrix: no ministry cell may describe fewer than 10 people.
K_ANONYMITY = 10
TENSION_DEFINITION_VERSION = "published-position-to-active-jobseeker-v1"


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


def labour_market_overview(
    db: Session, *, period_start: date, period_end: date, limit: int = 5
) -> tuple[list[GovernorateDemandCell], list[OccupationTensionCell], int, date, date]:
    """Aggregate published role demand against jobseekers' desired occupations.

    Cells with a non-zero candidate cohort smaller than k are omitted. No
    candidate records or identifiers leave this service.
    """
    duration = (period_end - period_start).days + 1
    previous_end = period_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=duration - 1)

    def demand_between(start: date, end: date):
        statement = (
            select(
                JobOffer.occupation_id,
                JobOffer.governorate_code,
                func.sum(JobOffer.positions_count),
                func.count(func.distinct(JobOffer.id)),
            )
            .where(
                JobOffer.status == OfferStatus.PUBLISHED,
                JobOffer.occupation_id.is_not(None),
                JobOffer.published_at >= start,
                JobOffer.published_at < end + timedelta(days=1),
            )
            .group_by(JobOffer.occupation_id, JobOffer.governorate_code)
        )
        return {
            (row[0], row[1]): (int(row[2] or 0), int(row[3] or 0))
            for row in db.execute(statement).all()
        }

    demand = demand_between(period_start, period_end)
    previous = demand_between(previous_start, previous_end)
    supply_statement = (
        select(
            CandidateDesiredOccupation.occupation_id,
            Candidate.governorate_code,
            func.count(func.distinct(Candidate.id)),
        )
        .join(Candidate, Candidate.id == CandidateDesiredOccupation.candidate_id)
        .where(Candidate.deleted_at.is_(None))
        .group_by(CandidateDesiredOccupation.occupation_id, Candidate.governorate_code)
    )
    supply = {
        (row[0], row[1]): int(row[2])
        for row in db.execute(supply_statement).all()
    }
    keys = set(demand) | set(supply)
    if not keys:
        return [], [], 0, previous_start, previous_end
    occupation_ids = {key[0] for key in keys}
    occupations = {
        row.id: row
        for row in db.execute(select(Occupation).where(Occupation.id.in_(occupation_ids))).scalars()
    }
    governorates = {
        row.code: row
        for row in db.execute(select(Governorate)).scalars()
    }

    suppressed = 0
    cells: list[OccupationTensionCell] = []
    demand_by_governorate: dict[str, list[int]] = {}
    for (occupation_id, governorate_code), (positions, offer_count) in demand.items():
        if governorate_code:
            totals = demand_by_governorate.setdefault(governorate_code, [0, 0])
            totals[0] += positions
            totals[1] += offer_count
    for key in keys:
        occupation_id, governorate_code = key
        positions, offer_count = demand.get(key, (0, 0))
        previous_positions = previous.get(key, (0, 0))[0]
        candidates = supply.get(key, 0)
        if positions == 0:
            continue
        if 0 < candidates < K_ANONYMITY:
            suppressed += 1
            continue
        occupation = occupations.get(occupation_id)
        if occupation is None:
            continue
        governorate = governorates.get(governorate_code)
        if governorate_code and governorate is None:
            continue
        label = governorate.name_fr if governorate else "National"
        ratio = round(positions / max(candidates, 1), 3)
        change = (
            round((positions - previous_positions) * 100 / previous_positions, 1)
            if previous_positions
            else (100.0 if positions else 0.0)
        )
        cells.append(
            OccupationTensionCell(
                occupation_code=occupation.code,
                occupation_title=occupation.title_fr,
                governorate_code=governorate_code,
                governorate_name=label,
                demand_positions=positions,
                published_offers=offer_count,
                candidate_supply=candidates,
                demand_supply_ratio=ratio,
                previous_demand_positions=previous_positions,
                demand_change_percent=change,
            )
        )
    cells.sort(key=lambda cell: (-cell.demand_supply_ratio, -cell.demand_positions, cell.occupation_code))
    governorate_cells = [
        GovernorateDemandCell(
            governorate_code=code,
            governorate_name=governorates[code].name_fr,
            demand_positions=totals[0],
            published_offers=totals[1],
        )
        for code, totals in demand_by_governorate.items()
        if code in governorates
    ]
    governorate_cells.sort(key=lambda item: (-item.demand_positions, item.governorate_name))
    return governorate_cells, cells[:limit], suppressed, previous_start, previous_end
