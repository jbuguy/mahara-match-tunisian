from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.career_roadmap import build_career_roadmap
from app.models import CandidateProfile, CandidateTechnicalAssessment, CandidateTechnicalAssessmentAnswer, Governorate, JobOffer, JobOfferStatus, Role, TechnicalAssessmentStatus, User
from app.security import create_access_token


def auth_headers(user: User) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_roadmap_is_deterministic_and_prioritizes_common_skill_gaps() -> None:
    offers = [
        SimpleNamespace(
            id="offer-b",
            title="Analyste",
            required_skills=["SQL", "Excel", "Python"],
        ),
        SimpleNamespace(
            id="offer-a",
            title="Développeuse",
            required_skills=["Python", "sql"],
        ),
    ]

    steps = build_career_roadmap(offers, [" Python "], {"sql": True})

    assert [(step.skill, step.offer_count, step.completed) for step in steps] == [
        ("SQL", 2, True),
        ("Excel", 1, False),
    ]
    assert steps[0].required_by == ["Analyste", "Développeuse"]
    assert [
        step.skill_key
        for step in build_career_roadmap(reversed(offers), ["Python"], {"sql": True})
    ] == ["sql", "excel"]


def test_candidate_can_update_only_their_current_roadmap_steps(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    session.add(Governorate(code="tunis", name_fr="Tunis", name_ar="تونس", latitude=36.8, longitude=10.2))
    session.add(JobOffer(
        employer_id=users[Role.EMPLOYER].id,
        title="Analyste de données",
        description="Analyser des données pour éclairer les décisions.",
        location="Tunis",
        required_skills=["SQL", "Excel"],
        status=JobOfferStatus.PUBLISHED,
    ))
    session.flush()
    employer_headers = auth_headers(users[Role.EMPLOYER])
    offer_response = client.post(
        "/employer/offers",
        headers=employer_headers,
        json={
            "title": "Analyste de données",
            "description": "Analyser des données pour éclairer les décisions.",
            "governorate_code": "tunis",
            "required_skills": ["SQL", "Excel"],
        },
    )
    assert offer_response.status_code == 201

    candidate_headers = auth_headers(users[Role.CANDIDATE])
    roadmap_response = client.get("/candidate/roadmap", headers=candidate_headers)
    assert roadmap_response.status_code == 200
    assert [step["skill"] for step in roadmap_response.json()["steps"]] == ["Excel", "SQL"]
    assert roadmap_response.json()["progress_percent"] == 0

    updated_response = client.put(
        "/candidate/roadmap/steps",
        headers=candidate_headers,
        json={"skill": "sql", "completed": True},
    )
    assert updated_response.status_code == 200
    assert updated_response.json()["completed_steps"] == 1
    assert updated_response.json()["total_steps"] == 2
    assert updated_response.json()["progress_percent"] == 50
    assert next(
        step for step in updated_response.json()["steps"] if step["skill_key"] == "sql"
    )["completed"]

    other_candidate = User(
        id="other-candidate",
        email="other-candidate@example.test",
        password_hash="unused",
        role=Role.CANDIDATE,
    )
    session.add(other_candidate)
    session.flush()
    other_headers = auth_headers(other_candidate)
    other_roadmap = client.get("/candidate/roadmap", headers=other_headers)
    assert other_roadmap.status_code == 200
    assert other_roadmap.json()["completed_steps"] == 0


def test_roadmap_rejects_non_candidate_roles_and_unknown_skills(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    for role, user in users.items():
        if role != Role.CANDIDATE:
            assert client.get(
                "/candidate/roadmap",
                headers=auth_headers(user),
            ).status_code == 403
    assert client.put(
        "/candidate/roadmap/steps",
        headers=auth_headers(users[Role.CANDIDATE]),
        json={"skill": "Nonexistent", "completed": True},
    ).status_code == 404


def test_candidate_can_persist_skill_exploration_goal(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    candidate = users[Role.CANDIDATE]
    session.add(CandidateProfile(user_id=candidate.id, skills=["Python"]))

    updated = client.put(
        "/candidate/roadmap/goal",
        headers=auth_headers(candidate),
        json={
            "goal_type": "skill_exploration",
            "title": "Développer mes compétences data",
            "skills": ["Python", " SQL ", "SQL"],
        },
    )

    assert updated.status_code == 200
    assert updated.json()["goal_type"] == "skill_exploration"
    assert updated.json()["goal_title"] == "Développer mes compétences data"
    assert updated.json()["selected_skills"] == ["Python", "SQL"]
    assert [step["skill"] for step in updated.json()["steps"]] == ["SQL"]
    assert client.get("/candidate/roadmap", headers=auth_headers(candidate)).json()["goal_title"] == "Développer mes compétences data"


def test_target_job_goal_uses_only_the_selected_published_offer(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    employer = users[Role.EMPLOYER]
    first = JobOffer(
        employer_id=employer.id,
        title="Développeur backend",
        description="Construire des API.",
        location="Tunis",
        required_skills=["Python", "SQL"],
        status=JobOfferStatus.PUBLISHED,
    )
    second = JobOffer(
        employer_id=employer.id,
        title="Analyste de données",
        description="Analyser les données.",
        location="Sfax",
        required_skills=["Excel"],
        status=JobOfferStatus.PUBLISHED,
    )
    session.add_all([first, second])
    session.flush()

    response = client.put(
        "/candidate/roadmap/goal",
        headers=auth_headers(users[Role.CANDIDATE]),
        json={"goal_type": "target_job", "title": first.title, "target_offer_id": first.id},
    )

    assert response.status_code == 200
    assert response.json()["target_offer_id"] == first.id
    assert {step["skill"] for step in response.json()["steps"]} == {"Python", "SQL"}


def test_candidate_can_track_practical_project_with_candidate_ownership(
    client: TestClient,
    users: dict[Role, User],
) -> None:
    candidate_headers = auth_headers(users[Role.CANDIDATE])
    goal = client.put(
        "/candidate/roadmap/goal",
        headers=candidate_headers,
        json={"goal_type": "skill_exploration", "title": "Apprendre Python", "skills": ["Python"]},
    )
    assert goal.status_code == 200
    assert goal.json()["steps"][0]["skill_key"] == "python"

    created = client.post(
        "/candidate/roadmap/projects",
        headers=candidate_headers,
        json={"skill": "python", "title": "API météo", "description": "Créer une API et documenter ses routes."},
    )
    assert created.status_code == 201
    project = created.json()
    assert project["skill"] == "Python"
    assert project["status"] == "planned"

    submitted = client.patch(
        f"/candidate/roadmap/projects/{project['id']}",
        headers=candidate_headers,
        json={"status": "submitted"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert client.get("/candidate/roadmap/projects", headers=candidate_headers).json()[0]["id"] == project["id"]

    assert client.patch(
        f"/candidate/roadmap/projects/{project['id']}",
        headers=auth_headers(users[Role.EMPLOYER]),
        json={"status": "in_progress"},
    ).status_code == 403
    assert client.post(
        "/candidate/roadmap/projects",
        headers=candidate_headers,
        json={"skill": "unknown", "title": "Projet", "description": "Test"},
    ).status_code == 404


def test_roadmap_assessments_reuse_candidate_assessment_results(
    client: TestClient,
    users: dict[Role, User],
    session: Session,
) -> None:
    offer = JobOffer(
        employer_id=users[Role.EMPLOYER].id,
        title="Développeur Python",
        description="Développer des services.",
        location="Tunis",
        required_skills=["Python"],
        status=JobOfferStatus.PUBLISHED,
    )
    session.add(offer)
    session.flush()
    assessment = CandidateTechnicalAssessment(
        candidate_id=users[Role.CANDIDATE].id,
        job_offer_id=offer.id,
        skill="Python",
        questions=[],
        status=TechnicalAssessmentStatus.COMPLETED,
    )
    session.add(assessment)
    session.flush()
    session.add(CandidateTechnicalAssessmentAnswer(
        assessment_id=assessment.id,
        question_id="q1",
        answer="Test answer",
        evaluation={"score": 8, "max_score": 10},
    ))
    session.flush()

    response = client.get(
        "/candidate/roadmap/assessments",
        headers=auth_headers(users[Role.CANDIDATE]),
    )
    assert response.status_code == 200
    assert response.json() == [{
        "assessment_type": "technical",
        "assessment_id": assessment.id,
        "skill": "Python",
        "status": "completed",
        "score": 8,
        "max_score": 10,
    }]
