import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from mahara_data.schemas.matching import (
    MatchResult,
    RankedMatches,
    Roadmap,
    SkillGapItem,
)

from cv_adapter import adapter_profil_vers_contrat
from cv_parser import build_profile_from_cv
from scoring import (
    calculer_match,
    classer_offres,
    detecter_gaps,
    generer_roadmap,
)


DATA_DIR = Path(__file__).parent / "data"
WP1_EXAMPLES_DIR = (
    Path(__file__).parent.parent / "data-layer-wp1" / "contracts" / "examples"
)


def test_existing_cv_ranks_backend_offer_first_and_builds_roadmap():
    brut = build_profile_from_cv(str(DATA_DIR / "cv_exemple.docx"), "cand_demo")
    profil = adapter_profil_vers_contrat(brut, governorate_code="TN-71")
    offres = [
        {
            "job_offer_id": "offre-backend",
            "min_years_experience": 3,
            "location": {"governorate_code": "TN-71"},
            "skills": [
                {"label_raw": "Python", "requirement": "required", "min_level": 3},
                {"label_raw": "Django", "requirement": "required", "min_level": 3},
                {"label_raw": "SQL", "requirement": "required", "min_level": 2},
                {"label_raw": "Kubernetes", "requirement": "preferred", "min_level": 2},
                {"label_raw": "Communication", "requirement": "preferred", "min_level": 2},
            ],
        },
        {
            "job_offer_id": "offre-agricole",
            "min_years_experience": 2,
            "location": {"governorate_code": "TN-51"},
            "skills": [
                {"label_raw": "Irrigation", "requirement": "required", "min_level": 2},
                {"label_raw": "Gestion des sols", "requirement": "required", "min_level": 2},
            ],
        },
    ]

    resultat = classer_offres(profil, offres)

    assert resultat["items"][0]["job_offer_id"] == "offre-backend"
    assert resultat["items"][0]["score_global"] == 83.3
    assert generer_roadmap(profil, offres[0]) is not None


def test_wp1_examples_validate_as_match_and_roadmap_contracts():
    profil = json.loads(
        (WP1_EXAMPLES_DIR / "candidate_profile.cv_upload.json").read_text(
            encoding="utf-8"
        )
    )
    offre = json.loads(
        (WP1_EXAMPLES_DIR / "job_offer.json").read_text(encoding="utf-8")
    )
    profil["candidate_id"] = str(uuid4())
    offre["job_offer_id"] = str(uuid4())

    result = classer_offres(profil, [offre])
    MatchResult(**result["items"][0])
    ranked = RankedMatches(**result)
    roadmap = generer_roadmap(profil, offre)

    assert ranked.items[0].job_offer_id == UUID(offre["job_offer_id"])
    assert roadmap is not None
    Roadmap(**roadmap)


def test_no_skills_produces_no_gaps_and_zero_skill_component_is_neutral():
    profil = {"skills": [], "years_experience": 0}
    offre = {
        "job_offer_id": str(uuid4()),
        "min_years_experience": 0,
        "skills": [],
    }

    resultat = calculer_match(profil, offre)

    assert resultat["breakdown"]["hard_skills"] == 100.0
    assert resultat["breakdown"]["soft_skills"] == 100.0
    assert resultat["gaps"] == []


def test_everything_matches_scores_100_and_has_no_roadmap():
    profil = {
        "candidate_id": str(uuid4()),
        "years_experience": 5,
        "location": {"governorate_code": "TN-71"},
        "skills": [
            {"label_raw": "Python", "skill_type": "hard", "level": 3},
            {"label_raw": "Communication", "skill_type": "soft", "level": 2},
        ],
    }
    offre = {
        "job_offer_id": str(uuid4()),
        "min_years_experience": 5,
        "location": {"governorate_code": "TN-71"},
        "skills": [
            {
                "label_raw": "Python",
                "requirement": "required",
                "min_level": 3,
            },
            {
                "label_raw": "Communication",
                "requirement": "required",
                "min_level": 2,
            },
        ],
    }

    resultat = calculer_match(profil, offre)

    assert resultat["score_global"] == 100.0
    assert resultat["gaps"] == []
    assert generer_roadmap(profil, offre) is None


def test_scores_are_bounded_between_zero_and_one_hundred():
    profil = {
        "years_experience": 100,
        "location": {"governorate_code": "TN-71"},
        "skills": [{"label_raw": "Python", "level": 4}],
    }
    offres = [
        {"skills": [], "min_years_experience": 0},
        {
            "skills": [
                {
                    "label_raw": "Unknown",
                    "requirement": "required",
                    "min_level": 4,
                }
            ],
            "min_years_experience": 2,
            "location": {"governorate_code": "TN-51"},
        },
        {
            "skills": [
                {
                    "label_raw": "Python",
                    "requirement": "required",
                    "min_level": 1,
                }
            ],
            "min_years_experience": 1,
            "location": {"governorate_code": "TN-71"},
        },
    ]

    scores = [calculer_match(profil, offre)["score_global"] for offre in offres]

    assert all(0 <= score <= 100 for score in scores)


def test_three_offers_have_stable_expected_ranking():
    profil = {
        "years_experience": 3,
        "location": {"governorate_code": "TN-71"},
        "skills": [
            {"label_raw": "Python", "level": 4},
            {"label_raw": "SQL", "level": 2},
        ],
    }
    offres = [
        {
            "job_offer_id": "python-best",
            "skills": [
                {
                    "label_raw": "Python",
                    "requirement": "required",
                    "min_level": 4,
                }
            ],
        },
        {
            "job_offer_id": "sql-middle",
            "skills": [
                {
                    "label_raw": "SQL",
                    "requirement": "required",
                    "min_level": 4,
                }
            ],
        },
        {
            "job_offer_id": "missing-last",
            "skills": [
                {
                    "label_raw": "Kubernetes",
                    "requirement": "required",
                    "min_level": 2,
                }
            ],
        },
    ]

    first_order = [
        item["job_offer_id"] for item in classer_offres(profil, offres)["items"]
    ]
    second_order = [
        item["job_offer_id"] for item in classer_offres(profil, offres)["items"]
    ]

    assert first_order == ["python-best", "sql-middle", "missing-last"]
    assert second_order == first_order


def test_gaps_distinguish_missing_and_insufficient_level():
    profil = {"skills": [{"skill_code": "SK-0101", "level": 1}]}
    offre = {
        "skills": [
            {
                "skill_code": "SK-0101",
                "requirement": "required",
                "min_level": 3,
            },
            {
                "skill_code": "SK-0102",
                "requirement": "preferred",
                "min_level": 2,
            },
        ]
    }

    gaps = detecter_gaps(profil, offre)

    assert [(gap["skill_code"], gap["gap_type"]) for gap in gaps] == [
        ("SK-0101", "insufficient_level"),
        ("SK-0102", "missing"),
    ]


@pytest.mark.xfail(
    strict=True,
    reason="Known defect for step B: candidate_id is null, but WP1 MatchResult requires a UUID.",
)
def test_match_with_missing_candidate_id_validates_against_wp1():
    resultat = calculer_match(
        {"candidate_id": None, "skills": []},
        {"job_offer_id": str(uuid4()), "skills": []},
    )

    MatchResult(**resultat)


@pytest.mark.xfail(
    strict=True,
    reason="Known defect for step C: gaps use label_raw when skill_code is absent.",
)
def test_gap_without_skill_code_validates_against_wp1():
    gap = detecter_gaps(
        {"skills": []},
        {
            "skills": [
                {
                    "label_raw": "Unmapped skill",
                    "requirement": "required",
                    "min_level": 2,
                }
            ]
        },
    )[0]

    SkillGapItem(**gap)


@pytest.mark.xfail(
    strict=True,
    reason="Known defect for step C: roadmap steps use label_raw without required skill_code.",
)
def test_roadmap_without_skill_code_validates_against_wp1():
    roadmap = generer_roadmap(
        {"candidate_id": str(uuid4()), "skills": []},
        {
            "job_offer_id": str(uuid4()),
            "skills": [
                {
                    "label_raw": "Unmapped skill",
                    "requirement": "required",
                    "min_level": 2,
                }
            ],
        },
    )

    assert roadmap is not None
    Roadmap(**roadmap)
