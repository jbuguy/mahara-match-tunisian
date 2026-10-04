import uuid
from pydantic import Field
from datetime import date
from mahara_data.enums import MarketDataOrigin, ProcessingStatus, RequirementLevel, SkillType
from mahara_data.schemas.common import Contract, TaxonomyCode
from mahara_data.schemas.market import MarketDatasetCreate, MarketIndicatorRecord


class SkillCreate(Contract):
    """Payload to add an entry to the national skills referential. Owned by WP5."""

    code: TaxonomyCode
    label_fr: str = Field(min_length=1, max_length=200)
    label_ar: str | None = Field(default=None, max_length=200)
    label_derja: str | None = Field(default=None, max_length=200)
    alt_labels: list[str] = Field(default_factory=list)
    description: str | None = None
    skill_type: SkillType


class SkillUpdate(Contract):
    """Editorial corrections only. Status changes go through their own routes."""

    label_fr: str | None = Field(default=None, min_length=1, max_length=200)
    label_ar: str | None = Field(default=None, max_length=200)
    label_derja: str | None = Field(default=None, max_length=200)
    alt_labels: list[str] | None = None
    description: str | None = None
    skill_type: SkillType | None = None


class RemovalOut(Contract):
    """Tells the caller what actually happened: a real delete, or a retirement."""

    code: str
    outcome: str  # "deleted" | "deprecated"

class SuggestionApprove(Contract):
    """Promote a suggestion into a new entry of the referential. The admin writes the code."""

    code: TaxonomyCode
    label_fr: str = Field(min_length=1, max_length=200)
    label_ar: str | None = Field(default=None, max_length=200)
    label_derja: str | None = Field(default=None, max_length=200)
    description: str | None = None
    skill_type: SkillType


class SuggestionMerge(Contract):
    """Attach the proposed label as a synonym of a skill that already exists."""

    code: TaxonomyCode

class OccupationCreate(Contract):
    """Payload to add an occupation to the national referential. Owned by WP5."""

    code: TaxonomyCode
    isco_code: str | None = Field(default=None, max_length=8)
    title_fr: str = Field(min_length=1, max_length=200)
    title_ar: str | None = Field(default=None, max_length=200)
    alt_titles: list[str] = Field(default_factory=list)
    description: str | None = None
    sector_code: TaxonomyCode | None = None


class OccupationUpdate(Contract):
    """Editorial corrections only. Status changes go through their own routes."""

    isco_code: str | None = Field(default=None, max_length=8)
    title_fr: str | None = Field(default=None, min_length=1, max_length=200)
    title_ar: str | None = Field(default=None, max_length=200)
    alt_titles: list[str] | None = None
    description: str | None = None
    sector_code: TaxonomyCode | None = None


class OccupationSkillWrite(Contract):
    """One requirement line: which skill, and whether it is mandatory."""

    skill_code: TaxonomyCode
    requirement: RequirementLevel


class OccupationSkillsReplace(Contract):
    """The complete requirement list. Replaces whatever was there before."""

    skills: list[OccupationSkillWrite] = Field(default_factory=list)

class MarketDatasetSubmission(Contract):
    """What the ministry deposits: one dataset header plus its normalized rows."""

    dataset: MarketDatasetCreate
    records: list[MarketIndicatorRecord] = Field(default_factory=list, max_length=5000)


class RecordRejection(Contract):
    """One row the pipeline could not keep, with its position so it can be fixed and resent."""

    index: int
    reason: str


class IngestionReport(Contract):
    """What the depositor gets back: what was kept, what was not, and why."""

    dataset_id: uuid.UUID
    job_id: uuid.UUID
    status: ProcessingStatus
    records_total: int
    records_ok: int
    records_failed: int
    rejections: list[RecordRejection] = Field(default_factory=list)


class MarketDatasetOut(Contract):
    """A deposited dataset, seen from the admin side."""

    dataset_id: uuid.UUID
    title: str
    origin: MarketDataOrigin
    publisher: str
    period_start: date
    period_end: date
    indicator_count: int
    job_id: uuid.UUID | None = None
    job_status: ProcessingStatus | None = None