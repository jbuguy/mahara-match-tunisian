import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.features.ministry.routers import analytics as ministry_analytics
from app.features.ministry.routers import suggestions as ministry_suggestions
from app.features.ministry.routers import taxonomy as ministry_taxonomy
from app.security import get_current_user
from mahara_data.db import Base
from mahara_data.db.models.accounts import User
from mahara_data.db.models.candidates import Candidate, CandidateSkill
from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.platform import AuditLog
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Skill, SkillSuggestion
from mahara_data.enums import (
    ContractType,
    IngestionSource,
    LiteracyLevel,
    OfferSource,
    OfferStatus,
    OnboardingPath,
    RequirementLevel,
    SkillSource,
    SkillType,
    SuggestionStatus,
    TaxonomyStatus,
    UserRole,
    WorkMode,
)


@pytest.fixture
def ministry_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    admin_id = uuid.uuid4()
    # require_roles() is a factory, so its dependency cannot be overridden directly:
    # overriding get_current_user unlocks every ministry router at once.
    admin = type("UserRef", (), {"id": admin_id, "roles": ["ministry_admin"]})()

    with sessions() as db:
        db.add(User(id=admin_id, role=UserRole.MINISTRY, email="admin@ministry.test", roles=["ministry_admin"]))
        db.commit()

    def override_get_db():
        with sessions() as db:
            yield db

    app = FastAPI()
    for router in (ministry_taxonomy.router, ministry_suggestions.router, ministry_analytics.router):
        app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin
    with TestClient(app) as client:
        yield client, sessions, admin_id
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_skill_is_created_as_draft_then_validated_with_audit_trail(ministry_client):
    client, sessions, admin_id = ministry_client

    created = client.post(
        "/api/v1/admin/taxonomy/skills",
        json={"code": "REM-E1204", "label_fr": "Soudure TIG", "skill_type": "hard"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == TaxonomyStatus.DRAFT.value

    validated = client.post("/api/v1/admin/taxonomy/skills/REM-E1204/validate")
    assert validated.status_code == 200
    assert validated.json()["status"] == TaxonomyStatus.VALIDATED.value

    with sessions() as db:
        skill = db.execute(select(Skill).where(Skill.code == "REM-E1204")).scalar_one()
        assert skill.validated_by == admin_id
        assert skill.validated_at is not None
        entries = db.execute(
            select(AuditLog).where(AuditLog.entity_type == "skill", AuditLog.entity_id == "REM-E1204").order_by(AuditLog.id)
        ).scalars().all()
        assert [entry.action for entry in entries] == ["skill.created", "skill.validated"]
        assert all(entry.actor_user_id == admin_id for entry in entries)


def test_approving_a_suggestion_creates_a_draft_and_a_second_verdict_conflicts(ministry_client):
    client, sessions, _admin_id = ministry_client
    suggestion_id = uuid.uuid4()
    with sessions() as db:
        db.add(
            SkillSuggestion(
                id=suggestion_id,
                proposed_label="soudure tig",
                normalized_label="soudure tig",
                skill_type=SkillType.HARD,
                source=IngestionSource.CV_UPLOAD,
                occurrences=4,
            )
        )
        db.commit()
    base = f"/api/v1/admin/taxonomy/suggestions/{suggestion_id}"

    approved = client.post(f"{base}/approve", json={"code": "REM-E1204", "label_fr": "Soudure TIG", "skill_type": "hard"})
    assert approved.status_code == 201
    # Approving is not validating: the new entry still needs its own validation act.
    assert approved.json()["status"] == TaxonomyStatus.DRAFT.value

    # A different code, so the conflict can only come from the closed suggestion.
    second = client.post(f"{base}/approve", json={"code": "REM-E1205", "label_fr": "Soudure TIG", "skill_type": "hard"})
    assert second.status_code == 409
    assert second.json()["detail"] == "Suggestion already reviewed: approved"

    with sessions() as db:
        suggestion = db.get(SkillSuggestion, suggestion_id)
        skill = db.execute(select(Skill).where(Skill.code == "REM-E1204")).scalar_one()
        assert suggestion.status == SuggestionStatus.APPROVED
        assert suggestion.resolved_skill_id == skill.id
        assert skill.status == TaxonomyStatus.DRAFT
        assert db.execute(select(Skill).where(Skill.code == "REM-E1205")).scalar_one_or_none() is None


def test_skill_gap_map_withholds_cells_of_one_to_nine_people_and_publishes_zero(ministry_client):
    client, sessions, _admin_id = ministry_client
    skills = {
        code: Skill(id=uuid.uuid4(), code=code, label_fr=code, skill_type=SkillType.HARD, status=TaxonomyStatus.VALIDATED)
        for code in ("REM-ONE", "REM-NINE", "REM-TEN", "REM-ZERO")
    }
    candidates = [
        Candidate(
            id=uuid.uuid4(),
            onboarding_path=OnboardingPath.CV_UPLOAD,
            literacy_level=LiteracyLevel.LITERATE,
            governorate_code="TN-11",
        )
        for _ in range(10)
    ]
    holders = {"REM-ONE": candidates[:1], "REM-NINE": candidates[:9], "REM-TEN": candidates}
    offer_id = uuid.uuid4()

    with sessions() as db:
        db.add(Governorate(code="TN-11", name_fr="Tunis", name_ar="تونس"))
        db.add_all([*skills.values(), *candidates])
        db.flush()
        db.add_all(
            [
                CandidateSkill(candidate_id=candidate.id, skill_id=skills[code].id, level=2, source=SkillSource.CV)
                for code, group in holders.items()
                for candidate in group
            ]
        )
        db.add(
            JobOffer(
                id=offer_id,
                title="Soudeur",
                description_raw="Soudure TIG en atelier.",
                contract_type=ContractType.CDI,
                work_mode=WorkMode.ON_SITE,
                governorate_code="TN-11",
                status=OfferStatus.PUBLISHED,
                source=OfferSource.MINISTRY_FEED,
                positions_count=1,
                min_years_experience=0,
                languages_required=[],
                published_at=datetime.now(timezone.utc) - timedelta(days=10),
            )
        )
        db.flush()
        db.add(JobOfferSkill(job_offer_id=offer_id, skill_id=skills["REM-ZERO"].id, requirement=RequirementLevel.REQUIRED))
        db.commit()

    response = client.get("/api/v1/admin/analytics/skill-gaps")

    assert response.status_code == 200
    body = response.json()
    assert body["k_anonymity"] == 10
    assert body["cells_suppressed"] == 2
    cells = {cell["skill_code"]: cell for cell in body["cells"]}
    assert set(cells) == {"REM-TEN", "REM-ZERO"}
    assert cells["REM-TEN"]["supply_count"] == 10
    assert cells["REM-ZERO"]["supply_count"] == 0
    assert cells["REM-ZERO"]["demand_count"] == 1
