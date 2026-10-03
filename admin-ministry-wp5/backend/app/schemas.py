from pydantic import Field

from mahara_data.enums import SkillType
from mahara_data.schemas.common import Contract, TaxonomyCode


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