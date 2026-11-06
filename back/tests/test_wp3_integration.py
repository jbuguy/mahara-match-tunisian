import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import User
from app.features.matching.router import create_matching_router
from app.features.matching.roadmaps import create_roadmap_router
from mahara_data.db import Base as SharedBase
from mahara_data.db.models.employers import JobOffer, JobOfferSkill
from mahara_data.db.models.matching import MatchResult as StoredMatchResult, Roadmap as StoredRoadmap, SkillGap
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Occupation, OccupationSkill, Skill, SkillRelation
from mahara_data.db.models.training import TrainingCourse, TrainingCourseSkill, TrainingProvider
from mahara_data.enums import (
    ContractType,
    CourseModality,
    OfferSource,
    OfferStatus,
    RequirementLevel,
    RoadmapItemStatus,
    SkillRelationType,
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
    app.include_router(create_matching_router(get_db, get_current_user, read_profile))
    app.include_router(create_roadmap_router(get_db, get_current_user, read_profile))
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
    assert payload["roadmap_id"]
    assert payload["progress_pct"] == 0


def test_missing_profile_and_unknown_offer_return_not_found(wp3_client):
    client, active_user, _user, other_user, _candidate_id, _offer_id, _reads, _sessions = wp3_client
    active_user["value"] = other_user

    missing_profile = client.get("/api/v1/me/matches")
    unknown_offer = client.get("/api/v1/me/matches/unknown-offer/roadmap")

    assert missing_profile.status_code == 404
    assert unknown_offer.status_code == 404


def test_occupation_roadmap_recommends_transferable_skills_courses_and_tracks_progress(wp3_client):
    client, active_user, _user, other_user, candidate_id, _offer_id, _reads, sessions = wp3_client
    now = datetime.now(timezone.utc)
    with sessions() as db:
        python = db.query(Skill).filter_by(code="SK-0101").one()
        sql = db.query(Skill).filter_by(code="SK-0102").one()
        javascript = Skill(
            code="SK-0201",
            label_fr="JavaScript",
            skill_type=SkillType.HARD,
            status=TaxonomyStatus.VALIDATED,
        )
        occupation = Occupation(
            code="OC-0101",
            title_fr="Développeur logiciel",
            status=TaxonomyStatus.VALIDATED,
        )
        low_evidence_occupation = Occupation(
            code="OC-0102",
            title_fr="Développeur de systèmes embarqués",
            status=TaxonomyStatus.VALIDATED,
        )
        provider = TrainingProvider(name="Centre public", provider_type="public")
        db.add_all([javascript, occupation, low_evidence_occupation, provider])
        db.flush()
        db.add_all([
            OccupationSkill(
                occupation_id=occupation.id,
                skill_id=python.id,
                requirement=RequirementLevel.REQUIRED,
            ),
            OccupationSkill(
                occupation_id=occupation.id,
                skill_id=javascript.id,
                requirement=RequirementLevel.REQUIRED,
            ),
            OccupationSkill(
                occupation_id=low_evidence_occupation.id,
                skill_id=python.id,
                requirement=RequirementLevel.REQUIRED,
            ),
            SkillRelation(
                source_skill_id=sql.id,
                target_skill_id=javascript.id,
                relation_type=SkillRelationType.RELATED,
            ),
        ])
        course = TrainingCourse(
            provider_id=provider.id,
            title="JavaScript fundamentals",
            modality=CourseModality.ONLINE,
            duration_hours=24,
            cost_tnd=0,
            language="fr",
            is_active=True,
        )
        db.add(course)
        introductory_course = TrainingCourse(
            provider_id=provider.id,
            title="JavaScript introduction",
            modality=CourseModality.ONLINE,
            duration_hours=8,
            cost_tnd=0,
            language="fr",
            is_active=True,
        )
        db.add(introductory_course)
        db.flush()
        db.add_all([
            TrainingCourseSkill(training_course_id=course.id, skill_id=javascript.id, target_level=3),
            TrainingCourseSkill(training_course_id=introductory_course.id, skill_id=javascript.id, target_level=1),
        ])

        current_offer = db.get(JobOffer, _offer_id)
        current_offer.occupation_id = occupation.id
        current_offer.published_at = now - timedelta(days=10)
        current_offer.positions_count = 4
        historical_offer = JobOffer(
            title="Développeur logiciel précédent",
            description_raw="Offre historique de test.",
            occupation_id=occupation.id,
            contract_type=ContractType.CDI,
            work_mode=WorkMode.ON_SITE,
            governorate_code="TN-71",
            status=OfferStatus.PUBLISHED,
            source=OfferSource.EMPLOYER_FORM,
            positions_count=3,
            min_years_experience=1,
            languages_required=[],
            published_at=now - timedelta(days=120),
        )
        db.add(historical_offer)
        db.commit()

    created = client.post(
        "/api/v1/me/roadmaps",
        json={"target_occupation_code": "OC-0101"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["candidate_id"] == str(candidate_id)
    assert payload["target_occupation_title"] == "Développeur logiciel"
    assert payload["market_signal"]["status"] == "increasing"
    assert payload["market_signal"]["current_positions"] == 4
    assert payload["market_signal"]["previous_positions"] == 3
    assert len(payload["steps"]) == 1
    assert payload["steps"][0]["skill_code"] == "SK-0201"
    assert payload["steps"][0]["transferable_skill_codes"] == ["SK-0102"]
    assert payload["steps"][0]["transferable_skills"] == [{"skill_code": "SK-0102", "label": "SQL"}]
    assert payload["steps"][0]["courses"][0]["title"] == "JavaScript fundamentals"
    assert [course["title"] for course in payload["steps"][0]["courses"]] == ["JavaScript fundamentals"]

    repeated = client.post(
        "/api/v1/me/roadmaps",
        json={"target_occupation_code": "OC-0101"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["roadmap_id"] == payload["roadmap_id"]
    progress = client.patch(
        f"/api/v1/me/roadmaps/{payload['roadmap_id']}/steps/1",
        json={"status": "done"},
    )
    assert progress.status_code == 200
    assert progress.json()["progress_pct"] == 100
    assert progress.json()["status"] == "completed"
    assert progress.json()["steps"][0]["status"] == RoadmapItemStatus.DONE.value

    options = client.get("/api/v1/me/roadmaps/career-options")
    assert options.status_code == 200
    suggested = next(item for item in options.json()["items"] if item["occupation_code"] == "OC-0101")
    assert suggested["market_signal"]["status"] == "increasing"
    assert suggested["transferable_skill_codes"] == ["SK-0102"]
    assert suggested["transferable_skills"] == [{"skill_code": "SK-0102", "label": "SQL"}]
    low_evidence = next(item for item in options.json()["items"] if item["occupation_code"] == "OC-0102")
    assert low_evidence["market_signal"]["status"] == "insufficient_data"
    assert low_evidence["market_signal"]["change_percent"] is None
    no_gap = client.post(
        "/api/v1/me/roadmaps",
        json={"target_occupation_code": "OC-0102"},
    )
    assert no_gap.status_code == 200
    assert no_gap.json()["status"] == "no_gap"

    invalid_target = client.post(
        "/api/v1/me/roadmaps",
        json={"target_job_offer_id": str(_offer_id), "target_occupation_code": "OC-0101"},
    )
    assert invalid_target.status_code == 422

    active_user["value"] = other_user
    unauthorized = client.get(f"/api/v1/me/roadmaps/{payload['roadmap_id']}")
    assert unauthorized.status_code == 404
    active_user["value"] = _user

    with sessions() as db:
        saved = db.query(StoredRoadmap).one()
        assert saved.candidate_id == candidate_id
        assert saved.progress_pct == 100


def test_matching_order_is_stable_for_equal_scores(wp3_client):
    client, _active_user, _user, _other_user, _candidate_id, offer_id, _reads, sessions = wp3_client

    with sessions() as db:
        offer = db.get(JobOffer, offer_id)
        second_offer = JobOffer(
            title="Another developer",
            description_raw="Build software.",
            contract_type=offer.contract_type,
            work_mode=offer.work_mode,
            governorate_code=offer.governorate_code,
            status=OfferStatus.PUBLISHED,
            source=OfferSource.EMPLOYER_FORM,
            positions_count=1,
            min_years_experience=offer.min_years_experience,
            languages_required=[],
        )
        db.add(second_offer)
        db.flush()
        skills_by_code = {
            skill.code: skill for skill in db.query(Skill).filter(Skill.code.in_(("SK-0101", "SK-0102"))).all()
        }
        db.add_all([
            JobOfferSkill(job_offer_id=second_offer.id, skill_id=skills_by_code["SK-0101"].id,
                          requirement=RequirementLevel.REQUIRED, min_level=3),
            JobOfferSkill(job_offer_id=second_offer.id, skill_id=skills_by_code["SK-0102"].id,
                          requirement=RequirementLevel.PREFERRED, min_level=3),
        ])
        db.commit()

    first = client.get("/api/v1/me/matches").json()["items"]
    second = client.get("/api/v1/me/matches").json()["items"]
    assert [item["job_offer_id"] for item in first] == [item["job_offer_id"] for item in second]
    assert [item["job_offer_id"] for item in first] == sorted(item["job_offer_id"] for item in first)
