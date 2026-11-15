"""Deterministic skill and curated-relationship scoring."""

from dataclasses import dataclass

from app.models import SkillCatalogue, SkillRelationship
from app.skill_catalog import normalize_skill_key


RELATED_SKILL_CREDIT_CAP = 0.55
FOUNDATIONAL_SKILL_CREDIT_CAP = 0.35


@dataclass(frozen=True)
class SkillScoringWeights:
    related_skill_cap: float = RELATED_SKILL_CREDIT_CAP
    foundational_skill_cap: float = FOUNDATIONAL_SKILL_CREDIT_CAP


@dataclass(frozen=True)
class SkillMatchExplanation:
    kind: str
    requirement: str
    evidence: str | None
    contribution: float
    source: str
    relationship_type: str | None = None
    confidence: float | None = None
    strength: float | None = None


@dataclass(frozen=True)
class SkillMatchScore:
    score: int | None
    direct_required: int | None
    related_required: int | None
    foundational_required: int | None
    mandatory_direct_coverage: int | None
    matched_skills: list[str]
    missing_skills: list[str]
    explanations: list[SkillMatchExplanation]


def _rounded_percent(value: float) -> int:
    return int(value * 100 + 0.5)


def score_skill_match(
    candidate_skills: list[str],
    required_skills: list[str],
    catalogue: list[SkillCatalogue],
    relationships: list[SkillRelationship],
    weights: SkillScoringWeights = SkillScoringWeights(),
) -> SkillMatchScore:
    unique_requirements: list[str] = []
    seen_requirements: set[str] = set()
    for requirement in required_skills:
        key = normalize_skill_key(requirement)
        if key and key not in seen_requirements:
            unique_requirements.append(requirement)
            seen_requirements.add(key)

    aliases: dict[str, str] = {}
    for skill in catalogue:
        for alias in (skill.canonical_name_fr, skill.canonical_name_en, *skill.aliases):
            aliases[normalize_skill_key(alias)] = skill.id

    candidate_keys = {normalize_skill_key(skill) for skill in candidate_skills}
    candidate_ids = {
        aliases[key] for key in candidate_keys if key in aliases
    }
    related_edges: dict[tuple[str, str], list[SkillRelationship]] = {}
    foundational_edges: dict[tuple[str, str], list[SkillRelationship]] = {}
    for edge in relationships:
        if edge.relation_type == "RELATED_TO":
            related_edges.setdefault((edge.from_skill_id, edge.to_skill_id), []).append(edge)
            related_edges.setdefault((edge.to_skill_id, edge.from_skill_id), []).append(edge)
        elif edge.relation_type == "FOUNDATION_OF":
            foundational_edges.setdefault((edge.from_skill_id, edge.to_skill_id), []).append(edge)

    direct_count = 0
    related_credit = 0.0
    foundational_credit = 0.0
    evidence_total = 0.0
    matched: list[str] = []
    missing: list[str] = []
    explanations: list[SkillMatchExplanation] = []

    for required in unique_requirements:
        required_key = normalize_skill_key(required)
        required_id = aliases.get(required_key)
        if required_key in candidate_keys or (
            required_id is not None and required_id in candidate_ids
        ):
            direct_count += 1
            evidence_total += 1.0
            matched.append(required)
            explanations.append(
                SkillMatchExplanation(
                    kind="direct_skill",
                    requirement=required,
                    evidence=next(
                        skill for skill in candidate_skills
                        if normalize_skill_key(skill) == required_key
                        or (
                            required_id is not None
                            and aliases.get(normalize_skill_key(skill)) == required_id
                        )
                    ),
                    contribution=1.0,
                    source="candidate_profile.skills",
                )
            )
            continue

        missing.append(required)
        candidates: list[tuple[float, SkillRelationship, str]] = []
        if required_id is not None:
            for candidate in candidate_skills:
                candidate_id = aliases.get(normalize_skill_key(candidate))
                if candidate_id is None:
                    continue
                for edge in related_edges.get((candidate_id, required_id), []):
                    contribution = min(edge.strength, weights.related_skill_cap) * edge.confidence
                    candidates.append((contribution, edge, "related_skill"))
                for edge in foundational_edges.get((candidate_id, required_id), []):
                    contribution = (
                        min(edge.strength, weights.foundational_skill_cap) * edge.confidence
                    )
                    candidates.append((contribution, edge, "foundational_skill"))

        if candidates:
            contribution, edge, kind = max(candidates, key=lambda item: item[0])
            evidence = next(
                candidate
                for candidate in candidate_skills
                if aliases.get(normalize_skill_key(candidate)) == edge.from_skill_id
                or (
                    kind == "related_skill"
                    and aliases.get(normalize_skill_key(candidate)) == edge.to_skill_id
                )
            )
            evidence_total += contribution
            if kind == "related_skill":
                related_credit += contribution
            else:
                foundational_credit += contribution
            explanations.append(
                SkillMatchExplanation(
                    kind=kind,
                    requirement=required,
                    evidence=evidence,
                    contribution=contribution,
                    source=edge.source,
                    relationship_type=edge.relation_type,
                    confidence=edge.confidence,
                    strength=edge.strength,
                )
            )
        else:
            explanations.append(
                SkillMatchExplanation(
                    kind="missing_required_skill",
                    requirement=required,
                    evidence=None,
                    contribution=0.0,
                    source="candidate_profile.skills",
                )
            )

    total = len(unique_requirements)
    score = _rounded_percent(evidence_total / total) if total else None
    direct_coverage = _rounded_percent(direct_count / total) if total else None
    related_coverage = _rounded_percent(related_credit / total) if total else None
    foundational_coverage = _rounded_percent(foundational_credit / total) if total else None
    return SkillMatchScore(
        score=score,
        direct_required=direct_coverage,
        related_required=related_coverage,
        foundational_required=foundational_coverage,
        mandatory_direct_coverage=direct_coverage,
        matched_skills=matched,
        missing_skills=missing,
        explanations=explanations,
    )
