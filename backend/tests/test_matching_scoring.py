from app.matching.scoring import score_skill_match
from app.models import SkillCatalogue, SkillRelationship


def _catalogue() -> list[SkillCatalogue]:
    return [
        SkillCatalogue(
            id="python",
            canonical_name_fr="Python",
            canonical_name_en="Python",
            aliases=[],
        ),
        SkillCatalogue(
            id="sql",
            canonical_name_fr="SQL",
            canonical_name_en="SQL",
            aliases=[],
        ),
        SkillCatalogue(
            id="data-analysis",
            canonical_name_fr="Data Analysis",
            canonical_name_en="Data Analysis",
            aliases=[],
        ),
    ]


def test_direct_skill_match_remains_full_credit_and_is_explained() -> None:
    result = score_skill_match(
        ["Python"],
        ["python"],
        _catalogue(),
        [],
    )

    assert result.score == 100
    assert result.direct_required == 100
    assert result.matched_skills == ["python"]
    assert result.missing_skills == []
    assert result.explanations[0].kind == "direct_skill"
    assert result.explanations[0].evidence == "Python"


def test_related_and_foundational_skills_are_partial_and_not_direct_matches() -> None:
    catalogue = _catalogue()
    relationships = [
        SkillRelationship(
            id="python-related-data",
            from_skill_id="python",
            to_skill_id="data-analysis",
            relation_type="RELATED_TO",
            strength=0.55,
            confidence=0.8,
            source="test",
        ),
        SkillRelationship(
            id="sql-foundation-data",
            from_skill_id="sql",
            to_skill_id="data-analysis",
            relation_type="FOUNDATION_OF",
            strength=0.35,
            confidence=0.8,
            source="test",
        ),
    ]

    related = score_skill_match(["Python"], ["Data Analysis"], catalogue, relationships)
    foundational = score_skill_match(["SQL"], ["Data Analysis"], catalogue, relationships)

    assert related.score == 44
    assert related.matched_skills == []
    assert related.missing_skills == ["Data Analysis"]
    assert related.explanations[0].kind == "related_skill"
    assert round(related.explanations[0].contribution, 2) == 0.44

    assert foundational.score == 28
    assert foundational.explanations[0].kind == "foundational_skill"


def test_only_best_evidence_counts_and_empty_requirements_are_unscored() -> None:
    catalogue = _catalogue()
    relationships = [
        SkillRelationship(
            id="python-related-data",
            from_skill_id="python",
            to_skill_id="data-analysis",
            relation_type="RELATED_TO",
            strength=0.55,
            confidence=0.8,
            source="test",
        ),
    ]

    multiple_evidence = score_skill_match(
        ["Python", "Python"],
        ["Data Analysis", "data analysis", "Unknown"],
        catalogue,
        relationships,
    )
    empty = score_skill_match(["Python"], [], catalogue, relationships)

    assert multiple_evidence.score == 22
    assert multiple_evidence.related_required == 22
    assert multiple_evidence.missing_skills == ["Data Analysis", "Unknown"]
    assert empty.score is None
    assert empty.mandatory_direct_coverage is None
    assert empty.explanations == []
