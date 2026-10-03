import uuid

import pytest
from sqlalchemy import func, select

from app.models import (
    Candidate,
    CandidateDesiredOccupation,
    CandidateEducation,
    CandidateExperience,
    CandidatePii,
    CandidateSkill,
    Occupation,
    Skill,
)

URL = "/api/v1/me/profile"


@pytest.fixture
def codes(db):
    """Three test skills and two test occupations; returns their codes."""
    tag = uuid.uuid4().hex[:6].upper()
    skills = [f"SK-T{tag}{i}" for i in range(1, 4)]
    occupations = [f"OC-T{tag}{i}" for i in range(1, 3)]
    db.add_all(
        Skill(code=code, label_fr=f"Compétence {code}", skill_type="hard", status="validated") for code in skills
    )
    db.add_all(Occupation(code=code, title_fr=f"Métier {code}") for code in occupations)
    db.flush()
    return {"skills": skills, "occupations": occupations}


def profile_body(codes, **overrides) -> dict:
    body = {
        "consent": True,
        "full_name": "Amira Ben Salah",
        "phone": "+216 20 123 456",
        "governorate_code": "TN-51",
        "education_level": "vocational_bts",
        "years_experience": 3,
        "languages": [{"code": "ar", "level": "native"}, {"code": "fr", "level": "fluent"}],
        "summary": "Vendeuse motivée.",
        "skills": [
            {"code": codes["skills"][0], "level": 3},
            {"code": codes["skills"][1], "level": 2},
        ],
        "experiences": [
            {"job_title_raw": "Vendeuse", "employer_name": "Monoprix", "start_date": "2022-01-01",
             "end_date": "2024-06-30", "duration_months": 30},
        ],
        "educations": [{"level": "vocational_bts", "field_of_study": "Commerce", "graduation_year": 2021}],
        "desired_occupations": [{"code": codes["occupations"][0]}, {"code": codes["occupations"][1]}],
    }
    body.update(overrides)
    return body


def count(db, table, where) -> int:
    return db.scalar(select(func.count()).select_from(table).where(where))


def candidate_of(db, user) -> Candidate | None:
    return db.scalar(select(Candidate).where(Candidate.user_id == user.id))


def test_get_profile_returns_404_when_none(client, signed_in):
    response = client.get(URL)
    assert response.status_code == 404


def test_put_creates_profile(client, signed_in, codes):
    response = client.put(URL, json=profile_body(codes))

    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["full_name"] == "Amira Ben Salah"
    assert profile["email"] == signed_in.email  # defaults to the login email
    assert profile["phone"] == "+216 20 123 456"
    assert profile["onboarding_path"] == "derja_detailed"
    assert profile["literacy_level"] == "literate"
    assert profile["governorate"]["name_fr"] == "Sousse"
    assert profile["consent_version"] == "1.0" and profile["consent_given_at"]
    assert profile["languages"] == [{"code": "ar", "level": "native"}, {"code": "fr", "level": "fluent"}]
    assert [(s["code"], s["level"], s["source"]) for s in profile["skills"]] == [
        (codes["skills"][0], 3, "self_declared"),
        (codes["skills"][1], 2, "self_declared"),
    ]
    assert profile["experiences"][0]["employer_name"] == "Monoprix"
    assert profile["educations"][0]["field_of_study"] == "Commerce"
    assert [(o["code"], o["priority"]) for o in profile["desired_occupations"]] == [
        (codes["occupations"][0], 1),
        (codes["occupations"][1], 2),
    ]

    assert client.get(URL).json() == profile


def test_put_from_cv_sets_onboarding_path(client, signed_in, codes):
    response = client.put(URL, json=profile_body(codes, from_cv=True))
    assert response.status_code == 200
    assert response.json()["onboarding_path"] == "cv_upload"


def test_put_again_updates_without_duplicates(client, db, signed_in, codes):
    first = client.put(URL, json=profile_body(codes)).json()

    body = profile_body(
        codes,
        full_name="Amira B. Salah",
        governorate_code="TN-11",
        skills=[{"code": codes["skills"][1], "level": 4}, {"code": codes["skills"][2], "level": 1}],
        experiences=[],
        desired_occupations=[{"code": codes["occupations"][1], "priority": 1}],
    )
    response = client.put(URL, json=body)

    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["full_name"] == "Amira B. Salah"
    assert profile["governorate"]["code"] == "TN-11"
    assert [(s["code"], s["level"]) for s in profile["skills"]] == [(codes["skills"][1], 4), (codes["skills"][2], 1)]
    assert profile["experiences"] == []
    assert [o["code"] for o in profile["desired_occupations"]] == [codes["occupations"][1]]
    assert profile["consent_given_at"] == first["consent_given_at"]  # stamped on the first save only

    candidate = candidate_of(db, signed_in)
    assert count(db, Candidate, Candidate.user_id == signed_in.id) == 1
    assert count(db, CandidatePii, CandidatePii.candidate_id == candidate.id) == 1
    assert count(db, CandidateSkill, CandidateSkill.candidate_id == candidate.id) == 2
    assert count(db, CandidateExperience, CandidateExperience.candidate_id == candidate.id) == 0
    assert count(db, CandidateEducation, CandidateEducation.candidate_id == candidate.id) == 1
    assert count(db, CandidateDesiredOccupation, CandidateDesiredOccupation.candidate_id == candidate.id) == 1


@pytest.mark.parametrize("consent", [False, None])
def test_put_requires_consent(client, db, signed_in, codes, consent):
    body = profile_body(codes)
    if consent is None:
        del body["consent"]
    else:
        body["consent"] = consent

    response = client.put(URL, json=body)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "consent"]
    assert candidate_of(db, signed_in) is None


def test_put_rejects_unknown_codes(client, db, signed_in, codes):
    body = profile_body(
        codes,
        governorate_code="TN-99",
        skills=[{"code": codes["skills"][0], "level": 2}, {"code": "SK-0000", "level": 2}],
        desired_occupations=[{"code": "OC-0000"}],
    )

    response = client.put(URL, json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert [(e["loc"], e["input"]) for e in errors] == [
        (["body", "governorate_code"], "TN-99"),
        (["body", "skills", 1, "code"], "SK-0000"),
        (["body", "desired_occupations", 0, "code"], "OC-0000"),
    ]
    assert candidate_of(db, signed_in) is None


def test_put_rejects_duplicate_skill_codes(client, signed_in, codes):
    skill = codes["skills"][0]
    body = profile_body(codes, skills=[{"code": skill, "level": 2}, {"code": skill, "level": 3}])
    response = client.put(URL, json=body)
    assert response.status_code == 422
    assert skill in response.json()["detail"][0]["msg"]


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_profile_requires_login(client, signed_out, method):
    response = client.request(method, URL, json={})
    assert response.status_code == 401
