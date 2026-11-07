from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Organisation,
    OrganisationMembership,
    OrganisationType,
    Role,
    User,
)
from app.security import create_access_token


def headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def add_organisation(session: Session, user: User, name: str) -> Organisation:
    organisation = Organisation(name=name, organisation_type=OrganisationType.EMPLOYER)
    session.add(organisation)
    session.flush()
    session.add(OrganisationMembership(user_id=user.id, organisation_id=organisation.id))
    session.flush()
    return organisation


def test_employer_planning_session_lifecycle_is_organisation_scoped(
    client: TestClient, session: Session, users: dict[Role, User]
) -> None:
    employer = users[Role.EMPLOYER]
    organisation = add_organisation(session, employer, "Studio Tunis")
    auth = headers(employer)

    created = client.post(
        "/employer/planning-sessions",
        headers=auth,
        json={
            "title": "Équipe marketing",
            "description": "Développer la présence numérique.",
            "project_type": "department",
        },
    )
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["organisation_id"] == organisation.id
    assert data["created_by_user_id"] == employer.id
    assert data["status"] == "draft"

    listing = client.get("/employer/planning-sessions", headers=auth)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [data["id"]]

    updated = client.patch(
        f"/employer/planning-sessions/{data['id']}",
        headers=auth,
        json={"title": "Équipe marketing numérique", "status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Équipe marketing numérique"
    assert updated.json()["status"] == "in_progress"

    archived = client.patch(
        f"/employer/planning-sessions/{data['id']}",
        headers=auth,
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    removed = client.delete(f"/employer/planning-sessions/{data['id']}", headers=auth)
    assert removed.status_code == 204
    assert client.get(f"/employer/planning-sessions/{data['id']}", headers=auth).status_code == 404


def test_planning_sessions_require_employer_membership_and_isolate_organisations(
    client: TestClient, session: Session, users: dict[Role, User]
) -> None:
    employer = users[Role.EMPLOYER]
    other_employer = User(
        email="other-employer@example.test",
        password_hash=employer.password_hash,
        role=Role.EMPLOYER,
    )
    session.add(other_employer)
    session.flush()
    add_organisation(session, employer, "First organisation")
    add_organisation(session, other_employer, "Other organisation")
    created = client.post(
        "/employer/planning-sessions",
        headers=headers(employer),
        json={"title": "Projet privé", "project_type": "new_project"},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    assert client.get(
        f"/employer/planning-sessions/{session_id}", headers=headers(other_employer)
    ).status_code == 404
    assert client.get(
        "/employer/planning-sessions", headers=headers(users[Role.CANDIDATE])
    ).status_code == 403


def test_planning_session_rejects_invalid_status_transition(
    client: TestClient, session: Session, users: dict[Role, User]
) -> None:
    employer = users[Role.EMPLOYER]
    add_organisation(session, employer, "Studio Tunis")
    created = client.post(
        "/employer/planning-sessions",
        headers=headers(employer),
        json={"title": "Projet", "project_type": "other"},
    )
    assert created.status_code == 201
    response = client.patch(
        f"/employer/planning-sessions/{created.json()['id']}",
        headers=headers(employer),
        json={"status": "completed"},
    )
    assert response.status_code == 409
