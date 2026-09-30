import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from mahara_data.schemas import (
    PUBLISHED_CONTRACTS,
    CandidateProfile,
    HiringFeedback,
    MarketIndicatorRecord,
    MatchResult,
    NormalizedJobOffer,
    RankedMatches,
    Roadmap,
    ScoringWeights,
    SkillGapItem,
)
from scripts.export_json_schemas import CONTRACTS_DIR, render

EXAMPLES = CONTRACTS_DIR / "examples"
EXAMPLE_MODELS = {
    "candidate_profile.cv_upload.json": CandidateProfile,
    "candidate_profile.derja_guided_voice.json": CandidateProfile,
    "job_offer.json": NormalizedJobOffer,
    "match_result.json": MatchResult,
    "roadmap.json": Roadmap,
    "hiring_feedback.json": HiringFeedback,
    "market_indicator.json": MarketIndicatorRecord,
}


def load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(EXAMPLE_MODELS))
def test_examples_are_valid(name):
    EXAMPLE_MODELS[name].model_validate(load(name))


def test_every_example_file_is_covered():
    assert {p.name for p in EXAMPLES.glob("*.json")} == set(EXAMPLE_MODELS)


@pytest.mark.parametrize("name", sorted(PUBLISHED_CONTRACTS))
def test_committed_json_schemas_are_up_to_date(name):
    path = CONTRACTS_DIR / f"{name}.schema.json"
    assert path.read_text(encoding="utf-8") == render(PUBLISHED_CONTRACTS[name]), (
        "Run `python -m scripts.export_json_schemas`"
    )


def _invalid(model, data, match):
    with pytest.raises(ValidationError, match=match):
        model.model_validate(data)


def test_unknown_fields_are_rejected():
    data = load("job_offer.json") | {"salary_negotiable": True}
    _invalid(NormalizedJobOffer, data, "Extra inputs are not permitted")


def test_unknown_governorate_is_rejected():
    data = load("job_offer.json")
    data["location"]["governorate_code"] = "TN-99"
    _invalid(NormalizedJobOffer, data, "Unknown governorate")


def test_cv_profile_requires_the_cv_document():
    data = load("candidate_profile.cv_upload.json") | {"source_document_ids": []}
    _invalid(CandidateProfile, data, "cv_upload profiles must reference")


def test_derja_profile_requires_its_conversation():
    data = load("candidate_profile.derja_guided_voice.json") | {"conversation_session_id": None}
    _invalid(CandidateProfile, data, "conversation_session_id")


def test_voice_path_is_for_non_literate_candidates():
    data = load("candidate_profile.derja_guided_voice.json") | {"literacy_level": "literate"}
    _invalid(CandidateProfile, data, "non-literate")


def test_profile_skill_needs_code_or_label():
    data = load("candidate_profile.cv_upload.json")
    data["skills"].append({"skill_type": "hard", "level": 2, "source": "cv"})
    _invalid(CandidateProfile, data, "skill_code or a label_raw")


def test_skill_level_is_bounded():
    data = load("candidate_profile.cv_upload.json")
    data["skills"][0]["level"] = 5
    _invalid(CandidateProfile, data, "less than or equal to 4")


def test_offer_needs_a_required_skill():
    data = load("job_offer.json")
    data["skills"] = [s | {"requirement": "preferred"} for s in data["skills"]]
    _invalid(NormalizedJobOffer, data, "at least one required skill")


def test_offer_salary_range_is_ordered():
    data = load("job_offer.json")
    data["salary"] = {"min_tnd": 3000, "max_tnd": 1000}
    _invalid(NormalizedJobOffer, data, "min_tnd must be <= max_tnd")


def test_default_weights_match_wp3_spec():
    w = ScoringWeights()
    assert (w.hard_skills, w.experience, w.soft_skills, w.location) == (0.5, 0.2, 0.15, 0.15)


def test_weights_must_sum_to_one():
    with pytest.raises(ValidationError, match="sum to 1.0"):
        ScoringWeights(hard_skills=0.6, experience=0.2, soft_skills=0.15, location=0.15)


def test_global_score_must_equal_weighted_breakdown():
    data = load("match_result.json") | {"score_global": 95}
    _invalid(MatchResult, data, "does not match the weighted breakdown")


def test_gap_levels_are_consistent():
    with pytest.raises(ValidationError, match="current_level < required_level"):
        SkillGapItem(skill_code="SK-1", gap_type="insufficient_level", requirement="required", required_level=2, current_level=3)
    with pytest.raises(ValidationError, match="no current_level"):
        SkillGapItem(skill_code="SK-1", gap_type="missing", requirement="required", required_level=2, current_level=1)


def test_ranked_matches_must_be_sorted():
    best = load("match_result.json")
    worse = copy.deepcopy(best) | {"score_global": 50.0}
    worse["breakdown"] = {"hard_skills": 50, "experience": 50, "soft_skills": 50, "location": 50}
    payload = {
        "subject_id": best["candidate_id"],
        "subject_type": "candidate",
        "generated_at": "2026-09-21T10:00:00Z",
    }
    RankedMatches.model_validate(payload | {"items": [best, worse]})
    _invalid(RankedMatches, payload | {"items": [worse, best]}, "sorted by score_global")


def test_roadmap_positions_are_contiguous():
    data = load("roadmap.json")
    data["steps"][1]["position"] = 3
    _invalid(Roadmap, data, "1..n")


def test_percent_indicator_is_bounded():
    data = load("market_indicator.json") | {"indicator_type": "unemployment_rate", "unit": "percent", "value": 140}
    _invalid(MarketIndicatorRecord, data, "between 0 and 100")
