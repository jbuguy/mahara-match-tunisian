import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics import record_event
from mahara_data.db.base import Base
from mahara_data.db.models.platform import AnalyticsEvent


def test_record_event_persists_normalized_structured_properties():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        user_id = uuid.uuid4()
        event = record_event(
            session,
            "candidate.signup_completed",
            actor_user_id=user_id,
            actor_role="Candidate",
            entity_type="candidate",
            entity_id=user_id,
            properties={"onboarding_path": "manual"},
        )
        session.commit()
        saved = session.query(AnalyticsEvent).one()
        assert event.id is not None
        assert saved.actor_role == "candidate"
        assert saved.properties == {"onboarding_path": "manual"}
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_record_event_rejects_large_property_maps():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        try:
            record_event(session, "test.event", properties={str(i): i for i in range(33)})
        except ValueError as error:
            assert "at most" in str(error)
        else:
            raise AssertionError("record_event accepted too many properties")
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
