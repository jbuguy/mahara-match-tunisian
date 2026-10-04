import json
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import EmployerDraftSession
from mahara_data.db import Base as SharedBase
from mahara_data.db.models.employers import Employer as SharedEmployer
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import CompanySize, SkillType, TaxonomyStatus
from employer_agent_wp4 import create_employer_agent_router
import employer_agent_wp4.router as employer_router


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=test_engine)


class FakeEmployer:
    def __init__(self, employer_id: uuid.UUID):
        self.id = employer_id


class FakeLLM:
    def __init__(self):
        self.last_input = None

    async def complete_chat(self, messages, **kwargs):
        import json

        self.last_input = json.loads(messages[-1]["content"])
        answer = self.last_input.get("answer", "")
        if answer.lower() in {"skip", "pass", "unknown"}:
            return '{"value": null, "skipped": true, "clarification": null}'
        if answer.lower() == "contradiction":
            return '{"value": null, "skipped": false, "clarification": "Pouvez-vous préciser votre préférence ?"}'
        return '{"value": "Développeur web", "skipped": false, "clarification": null}'


employer = FakeEmployer(uuid.uuid4())
other_employer = FakeEmployer(uuid.uuid4())
fake_llm = FakeLLM()


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def current_employer():
    return employer


app = FastAPI()
app.include_router(
    create_employer_agent_router(
        get_db,
        current_employer,
        EmployerDraftSession,
        llm_client=fake_llm,
    )
)
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=test_engine)
    SharedBase.metadata.drop_all(bind=test_engine)
    SharedBase.metadata.create_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    with TestSession() as db:
        db.add(Governorate(code="TN-11", name_fr="Tunis", name_ar="تونس"))
        db.add(
            SharedEmployer(
                id=employer.id,
                company_name="Test Employer",
                email="employer@example.com",
                password_hash="unused",
                sector="Technology",
                company_size=CompanySize.SMALL,
            )
        )
        db.add(
            Skill(
                code="SK-0001",
                label_fr="Développement web",
                skill_type=SkillType.HARD,
                status=TaxonomyStatus.VALIDATED,
            )
        )
        db.commit()


def create_session_with_draft():
    draft = {
        "title": "Développeur web",
        "description": "Développer et maintenir les fonctionnalités du site web.",
        "contract_type": "cdi",
        "work_mode": "hybrid",
        "location": {"governorate_code": "TN-11", "delegation": "Tunis"},
        "positions_count": 1,
        "min_years_experience": 0,
        "skills": [{"skill_code": "SK-0001", "requirement": "required", "min_level": 1}],
        "languages_required": [],
        "employer_id": str(employer.id),
        "status": "draft",
        "source": "employer_form",
    }
    db = TestSession()
    session = EmployerDraftSession(
        employer_id=employer.id,
        state={"field_index": 11, "answers": {}, "skipped": []},
        messages=[],
        draft=draft,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    session_id = session.id
    db.close()
    return session_id, draft


def test_session_starts_and_can_be_resumed_by_its_employer():
    created = client.post("/employer-agent/sessions")

    assert created.status_code == 201
    body = created.json()
    assert body["messages"][-1]["content"].startswith("Chnowa esm el poste?")
    assert body["draft"] is None

    resumed = client.get(f"/employer-agent/sessions/{body['id']}")

    assert resumed.status_code == 200
    assert resumed.json()["id"] == body["id"]
    assert resumed.json()["mode"] == "chat"


def test_form_mode_is_persisted_and_starts_without_chat_message():
    created = client.post("/employer-agent/sessions", json={"mode": "form"})

    assert created.status_code == 201
    assert created.json()["mode"] == "form"
    assert created.json()["messages"] == []
    assert client.get(f"/employer-agent/sessions/{created.json()['id']}").json()["mode"] == "form"


def test_session_rejects_unknown_mode():
    response = client.post("/employer-agent/sessions", json={"mode": "wizard"})

    assert response.status_code == 422


def test_session_cannot_be_read_by_another_employer():
    created = client.post("/employer-agent/sessions").json()
    app.dependency_overrides[current_employer] = lambda: other_employer

    response = client.get(f"/employer-agent/sessions/{created['id']}")

    assert response.status_code == 404
    app.dependency_overrides[current_employer] = current_employer


def test_session_list_is_scoped_to_the_signed_in_employer():
    created = client.post("/employer-agent/sessions").json()
    app.dependency_overrides[current_employer] = lambda: other_employer

    response = client.get("/employer-agent/sessions")

    assert response.status_code == 200
    assert all(session["id"] != created["id"] for session in response.json())
    app.dependency_overrides[current_employer] = current_employer


def test_served_ui_loads_the_built_react_app():
    response = client.get("/employer-agent/")

    assert response.status_code == 200
    assert 'id="root"' in response.text
    assert "/employer-agent/assets/index-" in response.text


def test_served_ui_exposes_built_assets():
    response = client.get("/employer-agent/")
    asset_path = response.text.split('src="', 1)[1].split('"', 1)[0]

    asset = client.get(asset_path)

    assert asset.status_code == 200
    assert "employers/login" in asset.text


def test_sample_generation_inputs_cover_distinct_job_types():
    samples_path = Path(__file__).resolve().parents[2] / "employer-agent-wp4" / "evals" / "job_types.json"
    samples = json.loads(samples_path.read_text(encoding="utf-8"))

    assert {sample["case"] for sample in samples} == {
        "retail-sales-assistant",
        "software-developer",
        "customer-support-agent",
        "seasonal-agricultural-worker",
    }
    assert all(sample["answers"].get("required_skills") for sample in samples)


def test_employer_can_edit_and_save_a_contract_valid_draft():
    session_id, draft = create_session_with_draft()
    draft["title"] = "Développeuse web junior"
    draft["source"] = "ministry_feed"
    draft["status"] = "published"

    response = client.patch(
        f"/employer-agent/sessions/{session_id}/draft",
        json={"draft": draft},
    )

    assert response.status_code == 200
    saved = response.json()["draft"]
    assert saved["title"] == "Développeuse web junior"
    assert saved["source"] == "employer_form"
    assert saved["status"] == "draft"
    assert saved["employer_id"] == str(employer.id)


def test_invalid_offer_edits_are_rejected():
    session_id, draft = create_session_with_draft()
    draft["title"] = "x"

    response = client.patch(
        f"/employer-agent/sessions/{session_id}/draft",
        json={"draft": draft},
    )

    assert response.status_code == 422


def test_editor_rejects_skill_codes_not_in_the_generated_taxonomy_matches():
    session_id, draft = create_session_with_draft()
    draft["skills"][0]["skill_code"] = "SK-UNVALIDATED"

    response = client.patch(
        f"/employer-agent/sessions/{session_id}/draft",
        json={"draft": draft},
    )

    assert response.status_code == 422
    assert "validated WP1 taxonomy" in response.json()["detail"]


def test_employer_can_publish_a_valid_draft():
    session_id, _ = create_session_with_draft()
    review = client.get(f"/employer-agent/sessions/{session_id}/review")
    assert review.status_code == 200

    response = client.post(f"/employer-agent/sessions/{session_id}/publish")

    assert response.status_code == 200
    published = response.json()["draft"]
    assert published["status"] == "published"
    assert published["source"] == "employer_form"
    assert published["offer_id"]
    assert published["published_at"]
    assert response.json()["messages"][-1]["content"] == "Votre offre est publiée et visible par les candidats."


def test_published_offer_cannot_be_edited_or_published_again():
    session_id, _ = create_session_with_draft()
    review = client.get(f"/employer-agent/sessions/{session_id}/review")
    assert review.status_code == 200
    published = client.post(f"/employer-agent/sessions/{session_id}/publish")
    draft = published.json()["draft"]

    edit_response = client.patch(f"/employer-agent/sessions/{session_id}/draft", json={"draft": draft})
    republish_response = client.post(f"/employer-agent/sessions/{session_id}/publish")

    assert edit_response.status_code == 409
    assert republish_response.status_code == 409


def test_first_answer_is_extracted_and_next_question_is_returned():
    created = client.post("/employer-agent/sessions").json()

    response = client.post(
        f"/employer-agent/sessions/{created['id']}/messages",
        json={"message": "Développeur web"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answers"]["title"] == "Développeur web"
    assert body["messages"][-1]["content"].startswith("Chnowa bech yaamel")


def test_form_submission_requires_core_offer_fields():
    created = client.post("/employer-agent/sessions", json={"mode": "form"}).json()

    response = client.post(
        f"/employer-agent/sessions/{created['id']}/answers",
        json={"answers": {"title": "Développeur web"}},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["missing_fields"] == [
        "responsibilities",
        "location",
        "contract_type",
        "required_skills",
    ]


def test_form_submission_generates_draft_and_tracks_skipped_optional_fields(monkeypatch):
    async def fake_generate_offer(client_arg, db, state, employer_id, skills_model):
        return create_session_with_draft()[1] | {"employer_id": employer_id}, []

    monkeypatch.setattr(employer_router, "generate_offer", fake_generate_offer)
    created = client.post("/employer-agent/sessions", json={"mode": "form"}).json()

    response = client.post(
        f"/employer-agent/sessions/{created['id']}/answers",
        json={
            "answers": {
                "title": "Développeur web",
                "responsibilities": "Développer et maintenir les fonctionnalités du site web.",
                "location": "Tunis",
                "contract_type": "CDI",
                "required_skills": "Python, APIs",
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["complete"] is True
    assert response.json()["skipped"] == [
        "preferred_skills",
        "experience_and_education",
        "languages_required",
        "work_mode",
        "positions_count",
        "salary",
    ]


def test_review_endpoint_returns_grounded_candidate_summary_without_salary_data():
    session_id, _ = create_session_with_draft()

    response = client.get(f"/employer-agent/sessions/{session_id}/review")

    assert response.status_code == 200
    review = response.json()
    assert review["salary"]["status"] == "not_provided"
    assert review["salary"]["benchmark"] is None
    assert review["candidate_snapshot"]["title"] == "Développeur web"
    assert review["candidate_snapshot"]["skills"][0]["label"] == "Développement web"


def test_skipped_required_answers_are_reasked_instead_of_lost():
    created = client.post("/employer-agent/sessions").json()

    for _ in range(11):
        response = client.post(
            f"/employer-agent/sessions/{created['id']}/messages",
            json={"message": "skip"},
        )
        assert response.status_code == 200

    body = response.json()
    assert body["complete"] is False
    assert body["skipped"][:5] == ["title", "responsibilities", "location", "contract_type", "required_skills"]
    assert body["messages"][-1]["content"].startswith("Chnowa esm el poste?")


def test_ambiguous_answer_pauses_without_advancing_the_interview():
    created = client.post("/employer-agent/sessions").json()
    client.post(
        f"/employer-agent/sessions/{created['id']}/messages",
        json={"message": "Développeur web"},
    )

    response = client.post(
        f"/employer-agent/sessions/{created['id']}/messages",
        json={"message": "contradiction"},
    )

    assert response.status_code == 200
    assert response.json()["answers"] == {"title": "Développeur web"}
    assert response.json()["messages"][-1]["content"] == "Pouvez-vous préciser votre préférence ?"
    assert fake_llm.last_input["prior_answers"] == {"title": "Développeur web"}