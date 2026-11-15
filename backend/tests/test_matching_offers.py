from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

from app.models import Governorate, Role, SkillCatalogue, SkillRelationship, User
from app.security import create_access_token


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def add_tunis_governorate(session: Session) -> None:
    session.add(
        Governorate(
            code="tunis",
            name_fr="Tunis",
            name_ar="تونس",
            latitude=36.8,
            longitude=10.2,
        )
    )
    session.flush()


def test_candidate_skills_are_normalized_and_used_for_matching(
    client: TestClient,
    session: Session,
    users: dict[Role, User],
) -> None:
    add_tunis_governorate(session)
    session.add_all(
        [
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
                id="excel",
                canonical_name_fr="Excel",
                canonical_name_en="Microsoft Excel",
                aliases=["Excel"],
            ),
        ]
    )
    session.flush()
    employer_headers = auth_headers(users[Role.EMPLOYER])
    offer_response = client.post(
        "/employer/offers",
        headers=employer_headers,
        json={
            "title": "Développeur Python",
            "description": "Concevoir et maintenir des outils internes.",
            "governorate_code": "tunis",
            "street_address": "Tunis",
            "required_skills": ["Python", "SQL", "python"],
        },
    )
    assert offer_response.status_code == 201
    assert offer_response.json()["required_skills"] == ["Python", "SQL"]

    candidate_headers = auth_headers(users[Role.CANDIDATE])
    profile_response = client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"skills": [" Python ", "PYTHON", "  Excel"]},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["skills"] == ["Python", "Excel"]

    matches_response = client.get("/candidate/matches", headers=candidate_headers)
    assert matches_response.status_code == 200
    assert matches_response.json()[0]["match_score"] == 50
    assert matches_response.json()[0]["matched_skills"] == ["Python"]
    assert matches_response.json()[0]["missing_skills"] == ["SQL"]
    assert matches_response.json()[0]["score_components"]["direct_required"] == 50
    assert matches_response.json()[0]["score_version"] == "skill-graph-v1"


def test_candidate_match_includes_partial_related_skill_explanation(
    client: TestClient,
    session: Session,
    users: dict[Role, User],
) -> None:
    add_tunis_governorate(session)
    session.add_all(
        [
            SkillCatalogue(
                id="python",
                canonical_name_fr="Python",
                canonical_name_en="Python",
                aliases=[],
            ),
            SkillCatalogue(
                id="data-analysis",
                canonical_name_fr="Data Analysis",
                canonical_name_en="Data Analysis",
                aliases=[],
            ),
        ]
    )
    session.flush()
    session.add(
        SkillRelationship(
            id="python-related-data",
            from_skill_id="python",
            to_skill_id="data-analysis",
            relation_type="RELATED_TO",
            strength=0.55,
            confidence=0.8,
            source="test",
        )
    )
    session.commit()

    offer_response = client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={
            "title": "Analyste de données",
            "description": "Analyser et restituer les données opérationnelles.",
            "governorate_code": "tunis",
            "street_address": "Tunis",
            "required_skills": ["Data Analysis"],
        },
    )
    assert offer_response.status_code == 201
    direct_offer_response = client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={
            "title": "Développeur Python",
            "description": "Développer et maintenir des applications Python.",
            "governorate_code": "tunis",
            "street_address": "Tunis",
            "required_skills": ["Python"],
        },
    )
    assert direct_offer_response.status_code == 201
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    assert client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"skills": ["Python"]},
    ).status_code == 200

    matches = client.get("/candidate/matches", headers=candidate_headers).json()
    assert [match["match_score"] for match in matches] == [100, 44]
    match = next(
        item for item in matches if item["id"] == offer_response.json()["id"]
    )

    assert match["match_score"] == 44
    assert match["matched_skills"] == []
    assert match["missing_skills"] == ["Data Analysis"]
    assert match["score_components"]["mandatory_direct_coverage"] == 0
    assert match["explanations"][0]["kind"] == "related_skill"
    assert match["explanations"][0]["evidence"] == "Python"
    assert match["explanations"][0]["requirement"] == "Data Analysis"


def test_employers_can_only_read_their_offers(
    client: TestClient,
    session: Session,
    users: dict[Role, User],
) -> None:
    add_tunis_governorate(session)
    response = client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={
            "title": "Chargé de projet",
            "description": "Coordonner les projets de transformation.",
            "governorate_code": "tunis",
            "street_address": "Sfax",
            "required_skills": ["Organisation"],
        },
    )
    assert response.status_code == 201

    own_offers = client.get(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
    )
    other_offers = client.get(
        "/employer/offers",
        headers=auth_headers(users[Role.TRAINING_PROVIDER]),
    )
    assert len(own_offers.json()) == 1
    assert other_offers.status_code == 403


def test_candidate_and_employer_routes_reject_other_roles(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    assert client.get(
        "/candidate/matches",
        headers=auth_headers(users[Role.EMPLOYER]),
    ).status_code == 403
    assert client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.CANDIDATE]),
        json={
            "title": "Chargé de projet",
            "description": "Coordonner les projets de transformation.",
            "location": "Sfax",
            "required_skills": ["Organisation"],
        },
    ).status_code == 403


def test_invalid_job_offer_is_not_published(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    response = client.post(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={
            "title": " ",
            "description": "Too short",
            "location": "Tunis",
            "required_skills": [],
        },
    )
    assert response.status_code == 422
    assert client.get(
        "/employer/offers",
        headers=auth_headers(users[Role.EMPLOYER]),
    ).json() == []
