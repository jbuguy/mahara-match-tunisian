"""Persistence adapters for platform workflows."""

from .accounts import get_candidate_for_user, get_employer_for_user, get_user_by_email
from .taxonomy import (
	get_skills_by_codes,
	get_validated_skills_by_codes,
	list_governorates,
	list_validated_skills,
	search_occupations,
	search_skills,
)

__all__ = [
	"get_candidate_for_user",
	"get_employer_for_user",
	"get_user_by_email",
	"get_skills_by_codes",
	"get_validated_skills_by_codes",
	"list_governorates",
	"list_validated_skills",
	"search_occupations",
	"search_skills",
]
