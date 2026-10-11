"""WP6 model names backed by WP1's canonical PostgreSQL mappings.

Keep these aliases so WP6's services stay readable and its local API remains
stable, while the shared package owns the tables, types, and migrations.
"""

from mahara_data.db.models.accounts import User
from mahara_data.db.models.candidates import (
    Candidate,
    CandidateDesiredOccupation,
    CandidateEducation,
    CandidateExperience,
    CandidatePII as CandidatePii,
    CandidateSkill,
)
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Occupation, Skill

ONBOARDING_PATHS = ("cv_upload", "derja_detailed", "derja_guided_voice")
LITERACY_LEVELS = ("literate", "basic", "non_literate")
SKILL_TYPES = ("hard", "soft", "language")
SKILL_SOURCES = ("self_declared", "cv", "dialogue", "certification", "employer_feedback")
SKILL_STATUSES = ("draft", "validated", "deprecated")
USER_ROLES = ("candidate", "employer", "admin", "ministry", "training_provider")
EDUCATION_LEVELS = (
    "none", "primary", "lower_secondary", "baccalaureate",
    "vocational_cap", "vocational_btp", "vocational_bts",
    "licence", "master", "engineer", "doctorate",
)

__all__ = [
    "Candidate",
    "CandidateDesiredOccupation",
    "CandidateEducation",
    "CandidateExperience",
    "CandidatePii",
    "CandidateSkill",
    "EDUCATION_LEVELS",
    "Governorate",
    "LITERACY_LEVELS",
    "Occupation",
    "ONBOARDING_PATHS",
    "SKILL_SOURCES",
    "SKILL_STATUSES",
    "SKILL_TYPES",
    "Skill",
    "USER_ROLES",
    "User",
]
