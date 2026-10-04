import asyncio
import json
import uuid
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import DateTime, ForeignKey, JSON, Uuid, create_engine, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from mahara_data.db import Base
from mahara_data.db.models.accounts import User
from mahara_data.db.models.employers import Employer, JobOffer, JobOfferSkill
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import CompanySize, SkillType, TaxonomyStatus, UserRole

from mahara_data.db.models.market import MarketDataset, MarketIndicator
from mahara_data.db.models.taxonomy import Occupation

from employer_agent_wp4.router import create_employer_agent_router
from employer_agent_wp4.workflow import build_offer_review, extract_answer, generate_offer


class EmployerDraftSessionFixture(Base):
    __tablename__ = "employer_draft_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employers.id"), nullable=False)
    state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    messages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    draft: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = 0
        self.response_format = None

    async def complete_chat(self, messages, **kwargs):
        self.calls += 1
        self.response_format = kwargs.get("response_format")
        return json.dumps(self.response)


class FakeQuery:
    def __init__(self, skills):
        self.skills = skills

    def filter(self, criterion):
        return self

    def all(self):
        return self.skills


class FakeDatabase:
    def __init__(self, skills):
        self.skills = skills

    def query(self, model):
        return FakeQuery(self.skills)


class ReviewQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *criteria):
        return self

    def order_by(self, *criteria):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class ReviewDatabase:
    def __init__(self, rows):
        self.rows = rows

    def query(self, model):
        return ReviewQuery(self.rows.get(model, []))

    def rollback(self):
        pass


def offer_payload(skill_code="SK-0001"):
    return {
        "title": "Vendeur en magasin",
        "description": "Accueillir les clients et organiser les produits en rayon.",
        "occupation_code": None,
        "sector_code": None,
        "contract_type": "cdd",
        "work_mode": "on_site",
        "location": {"governorate_code": "TN-11", "delegation": "Tunis"},
        "positions_count": 2,
        "min_years_experience": 0,
        "education_level_min": None,
        "salary": None,
        "skills": [{"skill_code": skill_code, "requirement": "required", "min_level": 1}],
        "languages_required": [],
        "status": "draft",
        "source": "employer_form",
    }


def complete_state():
    return {
        "answers": {
            "title": "Vendeur en magasin",
            "responsibilities": "Accueillir les clients et organiser les produits en rayon.",
            "location": "Tunis",
            "contract_type": "CDD",
            "required_skills": "Accueil client",
        },
        "skipped": ["salary"],
    }


def validated_skill(code="SK-0001"):
    return SimpleNamespace(code=code, label_fr="Accueil client", label_derja="ist9bel el clients")


def test_incomplete_answers_are_returned_without_calling_llm():
    client = FakeLLM(offer_payload())
    state = {"answers": {"title": "Vendeur"}, "skipped": []}

    result, missing = asyncio.run(
        generate_offer(client, FakeDatabase([validated_skill()]), state, "employer-id", Skill)
    )

    assert result is None
    assert "responsibilities" in missing
    assert client.calls == 0


def test_published_offer_and_skills_are_persisted_in_wp1_tables():
    engine = create_engine("sqlite://")
    tables = [
        User.__table__,
        Governorate.__table__,
        Skill.__table__,
        Employer.__table__,
        JobOffer.__table__,
        JobOfferSkill.__table__,
        EmployerDraftSessionFixture.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)

    with Session(engine) as db:
        user = User(email="employer@example.com", role=UserRole.EMPLOYER)
        db.add(user)
        db.flush()
        employer = Employer(
            user_id=user.id,
            company_name="Carthage Digital",
            email="employer@example.com",
            password_hash="not-used-in-this-test",
            sector="Technology",
            company_size=CompanySize.SMALL,
        )
        governorate = Governorate(code="TN-11", name_fr="Tunis", name_ar="Tunis")
        skill = Skill(
            code="SK-0001",
            label_fr="Accueil client",
            skill_type=SkillType.HARD,
            status=TaxonomyStatus.VALIDATED,
        )
        db.add_all([employer, governorate, skill])
        db.flush()

        draft_session = EmployerDraftSessionFixture(
            employer_id=employer.id,
            state={"mode": "chat"},
            messages=[],
            draft=offer_payload(),
        )
        draft_session.draft["employer_id"] = str(employer.id)
        db.add(draft_session)
        db.flush()

        router = create_employer_agent_router(lambda: None, lambda: None, EmployerDraftSessionFixture)
        review_offer = next(route.endpoint for route in router.routes if route.path.endswith("/review"))
        publish = next(route.endpoint for route in router.routes if route.path.endswith("/publish"))
        with pytest.raises(HTTPException) as error:
            publish(session_id=draft_session.id, current=employer, db=db)
        assert error.value.status_code == 409

        review_offer(session_id=draft_session.id, current=employer, db=db)
        response = publish(session_id=draft_session.id, current=employer, db=db)
        db.refresh(draft_session)

        persisted_id = uuid.UUID(response["draft"]["offer_id"])
        persisted_offer = db.get(JobOffer, persisted_id)
        persisted_skill = db.get(JobOfferSkill, (persisted_id, skill.id))
        assert response["draft"]["status"] == "published"
        assert draft_session.draft["status"] == "published"
        assert persisted_offer is not None
        assert persisted_offer.employer_id == employer.id
        assert persisted_offer.title == "Vendeur en magasin"
        assert persisted_offer.status.value == "published"
        assert persisted_skill is not None
        assert persisted_skill.requirement.value == "required"


def test_answer_extraction_uses_lm_studio_json_schema_mode():
    client = FakeLLM({"value": "Développeur web", "skipped": False, "clarification": None})

    result = asyncio.run(extract_answer(client, "title", "Développeur web"))

    assert result == ("Développeur web", False, None)
    assert client.response_format["type"] == "json_schema"
    assert client.response_format["json_schema"]["schema"]["required"] == [
        "value",
        "skipped",
        "clarification",
    ]


def test_generation_returns_wp1_validated_offer_with_employer_id():
    client = FakeLLM(offer_payload())

    result, missing = asyncio.run(
        generate_offer(client, FakeDatabase([validated_skill()]), complete_state(), "11111111-1111-4111-8111-111111111111", Skill)
    )

    assert missing == []
    assert result["title"] == "Vendeur en magasin"
    assert result["employer_id"] == "11111111-1111-4111-8111-111111111111"
    assert result["skills"][0]["skill_code"] == "SK-0001"
    assert client.response_format["type"] == "json_schema"
    assert client.response_format["json_schema"]["name"] == "normalized_job_offer"


def test_generation_rejects_skill_codes_absent_from_validated_taxonomy():
    client = FakeLLM(offer_payload("SK-FAKE"))

    result, missing = asyncio.run(
        generate_offer(
            client,
            FakeDatabase([validated_skill()]),
            complete_state(),
            "11111111-1111-4111-8111-111111111111",
            Skill,
        )
    )

    assert result is None
    assert missing == ["unrecognized_skill_codes"]


def test_generation_stays_incomplete_when_validated_taxonomy_is_empty():
    client = FakeLLM(offer_payload())

    result, missing = asyncio.run(
        generate_offer(client, FakeDatabase([]), complete_state(), "employer-id", Skill)
    )

    assert result is None
    assert missing == ["validated_skill_taxonomy"]
    assert client.calls == 0


def test_offer_review_compares_salary_only_with_matching_dated_market_data():
    occupation = SimpleNamespace(id="occupation-id")
    indicator = SimpleNamespace(
        value=1500,
        extra={"period": "month"},
        dataset_id="dataset-id",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 8, 31),
    )
    dataset = SimpleNamespace(title="Employment survey", publisher="Ministry of Employment")
    draft = offer_payload() | {
        "occupation_code": "OC-0001",
        "salary": {"min_tnd": 1400, "max_tnd": 1800, "period": "month"},
    }
    database = ReviewDatabase(
        {
            Occupation: [occupation],
            MarketIndicator: [indicator],
            MarketDataset: [dataset],
            Skill: [validated_skill()],
        }
    )

    review = build_offer_review(database, draft, today=date(2026, 9, 30))

    assert review["salary"]["status"] == "matched"
    assert review["salary"]["comparison"] == "includes_median"
    assert review["salary"]["benchmark"]["publisher"] == "Ministry of Employment"
    assert review["salary"]["benchmark"]["period_end"] == "2026-08-31"
    assert review["candidate_snapshot"]["skills"][0]["label"] == "Accueil client"


def test_offer_review_marks_old_salary_data_stale():
    occupation = SimpleNamespace(id="occupation-id")
    indicator = SimpleNamespace(
        value=1500,
        extra={"period": "month"},
        dataset_id="dataset-id",
        period_start=date(2020, 1, 1),
        period_end=date(2020, 12, 31),
    )
    draft = offer_payload() | {
        "occupation_code": "OC-0001",
        "salary": {"min_tnd": 1400, "max_tnd": 1800, "period": "month"},
    }
    database = ReviewDatabase(
        {
            Occupation: [occupation],
            MarketIndicator: [indicator],
            MarketDataset: [SimpleNamespace(title="Old survey", publisher="Publisher")],
        }
    )

    review = build_offer_review(database, draft, today=date(2026, 9, 30))

    assert review["salary"]["status"] == "stale"
    assert review["salary"]["benchmark"]["median_tnd"] == 1500


def test_offer_review_suggests_rechecking_experience_and_education_thresholds():
    draft = offer_payload() | {
        "min_years_experience": 6,
        "education_level_min": "master",
        "skills": [
            {"skill_code": f"SK-{index}", "requirement": "required", "min_level": 1}
            for index in range(5)
        ],
    }

    review = build_offer_review(ReviewDatabase({}), draft)

    assert {item["field"] for item in review["requirement_suggestions"]} == {
        "skills",
        "min_years_experience",
        "education_level_min",
    }