import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import User
from app.wp3_integration import create_wp3_router
from mahara_data.db import Base as SharedBase
from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.matching import MatchResult as StoredMatchResult, SkillGap
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import (
    ContractType,
    OfferSource,
    OfferStatus,
    RequirementLevel,
    SkillType,
    TaxonomyStatus,
    WorkMode,
)


@pytest.fixture
def wp3_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SharedBase.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    user = User(id=uuid.uuid4(), email="candidate@example.com", roles=["candidate"])
    other_user = User(id=uuid.uuid4(), email="other@example.com", roles=["candidate"])
    active_user = {"value": user}
    candidate_id = uuid.uuid4()
    offer_id = uuid.uuid4()
    profile = {
        "years_experience": 3,
        "governorate": {"code": "TN-71"},
        "skills": [
            {"code": "SK-0101", "label_fr": "Python", "skill_type": "hard", "level": 3},
            {"code": "SK-0102", "label_fr": "SQL", "skill_type": "hard", "level": 2},
        ],
    }
    reads = []

    def get_db():
        with TestSession() as db:
            yield db

    def get_current_user():
        return active_user["value"]

    def read_profile(_db, user_id):
        reads.append(user_id)
        if user_id == user.id:
            return candidate_id, profile
        return None

    with TestSession() as db:
        db.add(Governorate(code="TN-71", name_fr="Gafsa", name_ar="قفصة"))
        python_skill = Skill(
            code="SK-0101",
            label_fr="Python",
            skill_type=SkillType.HARD,
            status=TaxonomyStatus.VALIDATED,
        )
        sql_skill = Skill(
            code="SK-0102",
            label_fr="SQL",
            skill_type=SkillType.HARD,
            status=TaxonomyStatus.VALIDATED,
        )
        db.add_all([python_skill, sql_skill])
        db.flush()
        db.add(
            JobOffer(
                id=offer_id,
                title="Développeur Python",
                description_raw="Développer des outils Python.",
                contract_type=ContractType.CDI,
                work_mode=WorkMode.ON_SITE,
                governorate_code="TN-71",
                status=OfferStatus.PUBLISHED,
                source=OfferSource.EMPLOYER_FORM,
                positions_count=1,
                min_years_experience=2,
                languages_required=[],
            )
        )
        db.add_all(
            [
                JobOfferSkill(
                    job_offer_id=offer_id,
                    skill_id=python_skill.id,
                    requirement=RequirementLevel.REQUIRED,
                    min_level=3,
                ),
                JobOfferSkill(
                    job_offer_id=offer_id,
                    skill_id=sql_skill.id,
                    requirement=RequirementLevel.PREFERRED,
                    min_level=3,
                ),
            ]
        )
        db.commit()

    app = FastAPI()
    app.include_router(create_wp3_router(get_db, get_current_user, read_profile))
    with TestClient(app) as client:
        yield client, active_user, user, other_user, candidate_id, offer_id, reads, TestSession
    SharedBase.metadata.drop_all(bind=engine)
    engine.dispose()


def test_matches_use_the_signed_in_candidates_saved_profile(wp3_client):
    client, _active_user, user, _other_user, candidate_id, offer_id, reads, TestSession = wp3_client

    response = client.get("/api/v1/me/matches")

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject_id"] == str(candidate_id)
    assert payload["subject_type"] == "candidate"
    assert payload["items"]
    assert payload["items"][0]["candidate_id"] == str(candidate_id)
    assert reads == [user.id]
    assert payload["items"][0]["job_offer_id"] == str(offer_id)
    assert payload["items"][0]["match_id"]
    with TestSession() as db:
        stored = db.query(StoredMatchResult).one()
        assert stored.candidate_id == candidate_id
        assert stored.job_offer_id == offer_id
        assert db.query(SkillGap).filter_by(match_result_id=stored.id).count() == 1


def test_roadmap_uses_canonical_offer_ids_and_valid_wp1_shape(wp3_client):
    client, _active_user, _user, _other_user, candidate_id, offer_id, _reads, _sessions = wp3_client

    response = client.get(f"/api/v1/me/matches/{offer_id}/roadmap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == str(candidate_id)
    assert payload["target_job_offer_id"]
    assert payload["steps"]


def test_missing_profile_and_unknown_offer_return_not_found(wp3_client):
    client, active_user, _user, other_user, _candidate_id, _offer_id, _reads, _sessions = wp3_client
    active_user["value"] = other_user

    missing_profile = client.get("/api/v1/me/matches")
    unknown_offer = client.get("/api/v1/me/matches/unknown-offer/roadmap")

    assert missing_profile.status_code == 404
    assert unknown_offer.status_code == 404