from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from ..reference import GOVERNORATES

SCHEMA_VERSION = "1.0"


def _check_governorate(code: str) -> str:
    if code not in GOVERNORATES:
        raise ValueError(f"Unknown governorate code {code!r}; expected ISO 3166-2:TN such as 'TN-11'")
    return code


GovernorateCode = Annotated[str, AfterValidator(_check_governorate)]
# 1 = beginner, 2 = intermediate, 3 = advanced, 4 = expert
ProficiencyLevel = Annotated[int, Field(ge=1, le=4)]
Score = Annotated[float, Field(ge=0, le=100)]
# Taxonomy codes, e.g. "SK-0042" (skill) or "OC-7112" (occupation).
TaxonomyCode = Annotated[str, Field(min_length=1, max_length=32)]


class Contract(BaseModel):
    """Base class for every inter-WP payload: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=False)


class LanguageSkill(Contract):
    code: str = Field(min_length=2, max_length=8, examples=["ar-TN", "fr", "en"])
    level: ProficiencyLevel


class Location(Contract):
    governorate_code: GovernorateCode
    delegation: str | None = Field(default=None, max_length=80)


class ApiError(Contract):
    code: str = Field(examples=["validation_error", "not_found"])
    message: str
    details: dict | None = None


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
