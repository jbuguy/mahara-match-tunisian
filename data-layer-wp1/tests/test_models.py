"""ORM smoke tests on SQLite: the end-to-end data flow between WPs fits the schema."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mahara_data import enums as e
from mahara_data.db import Base
from mahara_data.db import models as m
from mahara_data.reference import EMBEDDING_DIM, GOVERNORATES


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(text("pragma foreign_keys = on"))
        Base.metadata.create_all(conn)
        with Session(bind=conn) as db:
            db.add_all(m.Governorate(code=c, name_fr=fr, name_ar=ar) for c, (fr, ar) in GOVERNORATES.items())
            db.flush()
            yield db


def _skill(db, code, skill_type=e.SkillType.HARD):
    skill = m.Skill(code=code, label_fr=code, skill_type=skill_type, status=e.TaxonomyStatus.VALIDATED)
    db.add(skill)
    db.flush()
    return skill


def test_full_flow_profile_offer_match_application_feedback(session):
    db = session
    python, php = _skill(db, "SK-0101"), _skill(db, "SK-0103")

    user = m.User(role=e.UserRole.CANDIDATE, phone="+21620123456")
    db.add(user)
    db.flush()
    candidate = m.Candidate(
        user_id=user.id,
        onboarding_path=e.OnboardingPath.CV_UPLOAD,
        literacy_level=e.LiteracyLevel.LITERATE,
        governorate_code="TN-51",
        years_experience=Decimal("2.0"),
    )
    db.add(candidate)
    db.flush()
    db.add(m.CandidatePII(candidate_id=candidate.id, full_name="Test Candidate"))
    db.add(m.CandidateSkill(candidate_id=candidate.id, skill_id=python.id, level=3, source=e.SkillSource.CV))

    employer = m.Employer(
        company_name="ACME",
        email="hr@acme.tn",
        password_hash="x",
        sector="IT",
        company_size=e.CompanySize.MEDIUM,
    )
    db.add(employer)
    db.flush()
    offer = m.JobOffer(
        employer_id=employer.id,
        title="Dev",
        description_raw="...",
        contract_type=e.ContractType.CDI,
        governorate_code="TN-51",
        status=e.OfferStatus.PUBLISHED,
    )
    db.add(offer)
    db.flush()
    db.add_all(
        [
            m.JobOfferSkill(job_offer_id=offer.id, skill_id=python.id, requirement=e.RequirementLevel.REQUIRED, min_level=3),
            m.JobOfferSkill(job_offer_id=offer.id, skill_id=php.id, requirement=e.RequirementLevel.PREFERRED, min_level=2),
        ]
    )

    match = m.MatchResult(
        candidate_id=candidate.id,
        job_offer_id=offer.id,
        score_global=Decimal("78.00"),
        score_hard_skills=Decimal("80"),
        score_experience=Decimal("70"),
        score_soft_skills=Decimal("75"),
        score_location=Decimal("85"),
        weights={"hard_skills": 0.5, "experience": 0.2, "soft_skills": 0.15, "location": 0.15},
        model_version="wp3-0.1",
    )
    db.add(match)
    db.flush()
    db.add(
        m.SkillGap(
            match_result_id=match.id,
            skill_id=php.id,
            gap_type=e.GapType.MISSING,
            requirement=e.RequirementLevel.PREFERRED,
            required_level=2,
        )
    )
    application = m.Application(candidate_id=candidate.id, job_offer_id=offer.id, match_result_id=match.id)
    db.add(application)
    db.flush()
    db.add(m.HiringFeedback(application_id=application.id, employer_id=employer.id, decision=e.HiringDecision.HIRED))

    roadmap = m.Roadmap(candidate_id=candidate.id, target_job_offer_id=offer.id, model_version="wp3-0.1")
    db.add(roadmap)
    db.flush()
    db.add(m.RoadmapItem(roadmap_id=roadmap.id, skill_id=php.id, position=1))

    db.add(
        m.Embedding(
            entity_type=e.EmbeddingEntity.CANDIDATE,
            entity_id=candidate.id,
            model_name="test-model",
            embedding=[0.0] * EMBEDDING_DIM,
            content_hash="0" * 64,
        )
    )
    db.flush()

    assert db.get(m.Application, application.id).status is e.ApplicationStatus.SUBMITTED


def test_enums_are_stored_by_value_not_name(session):
    db = session
    db.add(m.Employer(company_name="A", email="a@a.tn", password_hash="x", sector="s", company_size=e.CompanySize.SMALL))
    db.flush()
    assert db.execute(text("select company_size from employers")).scalar_one() == "1-10"


def test_candidate_skill_level_is_bounded(session):
    db = session
    skill = _skill(db, "SK-1")
    candidate = m.Candidate(onboarding_path=e.OnboardingPath.DERJA_DETAILED, literacy_level=e.LiteracyLevel.LITERATE)
    db.add(candidate)
    db.flush()
    db.add(m.CandidateSkill(candidate_id=candidate.id, skill_id=skill.id, level=5, source=e.SkillSource.DIALOGUE))
    with pytest.raises(IntegrityError):
        db.flush()


def test_user_needs_email_or_phone(session):
    session.add(m.User(role=e.UserRole.ADMIN))
    with pytest.raises(IntegrityError):
        session.flush()


def test_one_application_per_candidate_and_offer(session):
    db = session
    candidate = m.Candidate(onboarding_path=e.OnboardingPath.DERJA_DETAILED, literacy_level=e.LiteracyLevel.LITERATE)
    offer = m.JobOffer(
        title="t", description_raw="d", contract_type=e.ContractType.SIVP, governorate_code="TN-11",
        source=e.OfferSource.MINISTRY_FEED,
    )
    db.add_all([candidate, offer])
    db.flush()
    db.add(m.Application(candidate_id=candidate.id, job_offer_id=offer.id))
    db.flush()
    db.add(m.Application(candidate_id=candidate.id, job_offer_id=offer.id))
    with pytest.raises(IntegrityError):
        db.flush()


def test_roadmap_requires_a_target(session):
    db = session
    candidate = m.Candidate(onboarding_path=e.OnboardingPath.DERJA_DETAILED, literacy_level=e.LiteracyLevel.LITERATE)
    db.add(candidate)
    db.flush()
    db.add(m.Roadmap(candidate_id=candidate.id, model_version="v"))
    with pytest.raises(IntegrityError):
        db.flush()
