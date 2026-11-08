from fastapi.testclient import TestClient

from app.models import Role, User
from app.security import create_access_token


def headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_candidate_discovery_requires_consent_and_opt_out_removes_pool_members(
    client: TestClient, users: dict[Role, User]
) -> None:
    employer_headers = headers(users[Role.EMPLOYER])
    candidate_headers = headers(users[Role.CANDIDATE])
    profile = client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={
            "full_name": "Private Candidate Name",
            "skills": ["Python", "SQL"],
            "location": "Tunis",
            "professional_headline": "Data analyst",
        },
    )
    assert profile.status_code == 200
    assert client.get("/employer/candidates", headers=employer_headers).json() == []

    opted_in = client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"employer_discoverable": True},
    )
    assert opted_in.status_code == 200
    results = client.get("/employer/candidates?skill=Python", headers=employer_headers)
    assert results.status_code == 200
    assert len(results.json()) == 1
    assert results.json()[0]["professional_headline"] == "Data analyst"
    assert "full_name" not in results.json()[0]
    assert "phone" not in results.json()[0]

    pool = client.post(
        "/employer/talent-pools", headers=employer_headers, json={"name": "Analystes"}
    )
    assert pool.status_code == 201
    saved = client.post(
        f"/employer/talent-pools/{pool.json()['id']}/members",
        headers=employer_headers,
        json={"candidate_id": users[Role.CANDIDATE].id, "private_note": "SQL confirmé"},
    )
    assert saved.status_code == 201
    assert len(client.get(
        f"/employer/talent-pools/{pool.json()['id']}/members", headers=employer_headers
    ).json()) == 1

    opted_out = client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"employer_discoverable": False},
    )
    assert opted_out.status_code == 200
    assert client.get("/employer/candidates", headers=employer_headers).json() == []
    assert client.get(
        f"/employer/talent-pools/{pool.json()['id']}/members", headers=employer_headers
    ).json() == []


def test_formal_offer_response_records_hire_outcome(
    client: TestClient, users: dict[Role, User]
) -> None:
    employer_headers = headers(users[Role.EMPLOYER])
    candidate_headers = headers(users[Role.CANDIDATE])
    offer = client.post(
        "/employer/offers",
        headers=employer_headers,
        json={"title": "Analyste", "description": "Analyser les données de l’entreprise.", "location": "Tunis", "required_skills": ["SQL"]},
    ).json()
    application = client.post(
        f"/candidate/applications/{offer['id']}", headers=candidate_headers
    ).json()
    assert client.put(
        f"/employer/applications/{application['id']}/status",
        headers=employer_headers,
        json={"status": "interview"},
    ).status_code == 200
    assert client.put(
        f"/employer/applications/{application['id']}/status",
        headers=employer_headers,
        json={"status": "offer_made"},
    ).status_code == 200
    decision = client.post(
        f"/employer/applications/{application['id']}/offer-decision",
        headers=employer_headers,
        json={"proposed_conditions": {"summary": "Full-time role"}},
    )
    assert decision.status_code == 201
    assert decision.json()["status"] == "pending"
    assert client.get(
        "/candidate/offer-decisions", headers=candidate_headers
    ).json()[0]["proposed_conditions"] == {"summary": "Full-time role"}
    accepted = client.patch(
        f"/candidate/offer-decisions/{decision.json()['id']}",
        headers=candidate_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert client.get("/candidate/applications", headers=candidate_headers).json()[0]["status"] == "hired"
