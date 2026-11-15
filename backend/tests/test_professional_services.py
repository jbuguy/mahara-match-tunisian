import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    CandidateProfile,
    ProfessionalProfile,
    ProfessionalProfileVisibility,
    Role,
    ServiceListing,
    ServiceListingStatus,
    User,
)
from app.security import create_access_token


def headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


PROFILE = {
    "display_name": "Amira",
    "headline": "Développeuse web",
    "introduction": "Je crée des sites accessibles.",
    "visibility": "public",
}
SERVICE = {
    "title": "Création de site web",
    "description": "Création de sites web adaptés aux petites entreprises.",
    "category": "Développement",
    "skills": ["React"],
    "service_mode": "remote",
    "price_type": "quote",
}


@pytest.mark.parametrize(
    "role",
    [Role.EMPLOYER, Role.MINISTRY_ADMIN, Role.TRAINING_PROVIDER, Role.OPERATOR],
)
def test_non_candidates_cannot_manage_professional_profiles_or_services(
    client: TestClient,
    users: dict[Role, User],
    role: Role,
) -> None:
    user_headers = headers(users[role])

    assert client.get("/me/professional-profile", headers=user_headers).status_code == 403
    assert client.put(
        "/me/professional-profile", headers=user_headers, json=PROFILE
    ).status_code == 403
    assert client.get("/me/services", headers=user_headers).status_code == 403
    assert client.post(
        "/me/services", headers=user_headers, json=SERVICE
    ).status_code == 403
    assert client.put(
        "/me/services/service-id", headers=user_headers, json=SERVICE
    ).status_code == 403
    assert client.patch(
        "/me/services/service-id/status",
        headers=user_headers,
        json={"status": "published"},
    ).status_code == 403


def test_candidates_publish_public_services_without_exposing_user_ids(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    candidate_headers = headers(users[Role.CANDIDATE])
    profile = client.put(
        "/me/professional-profile",
        headers=candidate_headers,
        json={**PROFILE, "visibility": "private"},
    )
    assert profile.status_code == 200
    assert profile.json()["public_id"] != users[Role.CANDIDATE].id

    created = client.post("/me/services", headers=candidate_headers, json=SERVICE)
    assert created.status_code == 201
    service_id = created.json()["id"]
    assert created.json()["status"] == "draft"
    assert client.get("/public/services").json()["total"] == 0
    assert client.patch(
        f"/me/services/{service_id}/status",
        headers=candidate_headers,
        json={"status": "published"},
    ).status_code == 409

    profile = client.put(
        "/me/professional-profile",
        headers=candidate_headers,
        json={**PROFILE, "visibility": "public"},
    )
    assert profile.status_code == 200
    published = client.patch(
        f"/me/services/{service_id}/status",
        headers=candidate_headers,
        json={"status": "published"},
    )
    assert published.status_code == 200

    public_list = client.get("/public/services")
    assert public_list.status_code == 200
    service = public_list.json()["items"][0]
    assert service["id"] == service_id
    assert service["owner_public_id"] == profile.json()["public_id"]
    assert "owner_user_id" not in service
    assert users[Role.CANDIDATE].id not in service.values()

    public_detail = client.get(f"/public/services/{service_id}")
    assert public_detail.status_code == 200
    assert "owner_user_id" not in public_detail.json()

    public_profiles = client.get("/public/professionals")
    assert public_profiles.status_code == 200
    professional = public_profiles.json()["items"][0]
    assert professional["id"] == profile.json()["public_id"]
    assert professional["id"] != users[Role.CANDIDATE].id
    assert client.get(f"/public/professionals/{professional['id']}").status_code == 200

    paused = client.patch(
        f"/me/services/{service_id}/status",
        headers=candidate_headers,
        json={"status": "paused"},
    )
    assert paused.status_code == 200
    assert client.get("/public/services").json()["total"] == 0
    assert client.get(f"/public/services/{service_id}").status_code == 404


def test_candidates_cannot_edit_another_candidates_service(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    owner_headers = headers(users[Role.CANDIDATE])
    client.put(
        "/me/professional-profile",
        headers=owner_headers,
        json=PROFILE,
    )
    created = client.post("/me/services", headers=owner_headers, json=SERVICE)
    service_id = created.json()["id"]

    other_candidate = User(
        email="other-candidate@example.test",
        password_hash="not-used-in-this-test",
        role=Role.CANDIDATE,
    )
    session.add(other_candidate)
    session.commit()
    other_headers = headers(other_candidate)
    response = client.put(
        f"/me/services/{service_id}",
        headers=other_headers,
        json=SERVICE,
    )

    assert response.status_code == 404


def test_candidate_and_professional_profiles_share_skills_without_losing_entries(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    candidate_headers = headers(users[Role.CANDIDATE])
    candidate_update = client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"skills": ["Excel"]},
    )
    assert candidate_update.status_code == 200

    professional_update = client.put(
        "/me/professional-profile",
        headers=candidate_headers,
        json={**PROFILE, "skills": ["Excel", "React"]},
    )
    assert professional_update.status_code == 200
    assert professional_update.json()["skills"] == ["Excel", "React"]
    assert client.get("/candidate/profile", headers=candidate_headers).json()["skills"] == [
        "Excel",
        "React",
    ]

    candidate_update = client.put(
        "/candidate/profile",
        headers=candidate_headers,
        json={"skills": ["Python"]},
    )
    assert candidate_update.json()["skills"] == ["Python"]
    assert client.get("/me/professional-profile", headers=candidate_headers).json()[
        "skills"
    ] == ["Python"]


def test_public_discovery_excludes_non_candidate_profiles_and_private_fields(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    employer = users[Role.EMPLOYER]
    profile = ProfessionalProfile(
        user_id=employer.id,
        display_name="Private account",
        headline="Not a candidate",
        visibility=ProfessionalProfileVisibility.PUBLIC,
    )
    session.add(profile)
    session.flush()
    session.add(
        ServiceListing(
            owner_user_id=employer.id,
            title="Unavailable service",
            description="This listing belongs to a non-candidate.",
            category="Other",
            service_mode="remote",
            price_type="quote",
            status=ServiceListingStatus.PUBLISHED,
        )
    )
    session.add(
        CandidateProfile(
            user_id=employer.id,
            full_name="Private account",
            phone="+216 00 000 000",
            birth_year=1990,
            street_address="Private street",
        )
    )
    session.commit()

    assert client.get("/public/services").json()["total"] == 0
    assert client.get("/public/professionals").json()["total"] == 0
