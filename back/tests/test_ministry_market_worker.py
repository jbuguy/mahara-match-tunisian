import pytest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.features.ministry import worker
from app.features.ministry.schemas import MarketDatasetSubmission
from app.features.ministry.services import market
from mahara_data.db.base import Base
from mahara_data.db.models.reference import Governorate
from mahara_data.db.models.taxonomy import Skill
from mahara_data.enums import MarketDataOrigin, MarketIndicatorType, SkillType


def _make_session():
    import mahara_data.db.models.market
    import mahara_data.db.models.platform
    import mahara_data.db.models.reference
    import mahara_data.db.models.taxonomy

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def _seed_reference_data(db):
    db.add(Governorate(code="TN-11", name_fr="Tunis", name_ar="تونس"))
    db.add(Skill(code="SK-100", label_fr="Python", skill_type=SkillType.HARD))
    db.commit()


def _submission(value: float) -> MarketDatasetSubmission:
    return MarketDatasetSubmission.model_validate(
        {
            "dataset": {
                "title": "demo-market",
                "origin": MarketDataOrigin.OFFICIAL,
                "publisher": "Ministry",
                "period_start": date(2024, 1, 1),
                "period_end": date(2024, 1, 31),
                "document_id": None,
            },
            "records": [
                {
                    "indicator_type": MarketIndicatorType.SKILL_DEMAND,
                    "skill_code": "SK-100",
                    "governorate_code": "TN-11",
                    "period_start": date(2024, 1, 1),
                    "period_end": date(2024, 1, 31),
                    "value": value,
                    "unit": "count",
                    "extra": {},
                }
            ],
        }
    )


def test_runtime_environment_prefers_app_env_for_production_checks():
    settings = Settings(app_env="production", environment="development")

    assert settings.runtime_environment == "production"
    assert settings.is_production is True
    assert settings.email_verification_required is True


def test_ministry_feed_headers_use_bearer_tokens():
    class DummySettings:
        ministry_market_feed_token = "secret-token"

    headers = worker._build_feed_headers(DummySettings())

    assert headers["Authorization"] == "Bearer secret-token"
    assert headers["Accept"] == "application/json"


def test_ministry_feed_url_requires_https_in_production(monkeypatch):
    class DummySettings:
        is_production = True

    monkeypatch.setattr(worker, "get_settings", lambda: DummySettings())

    with pytest.raises(ValueError, match="HTTPS in production"):
        worker._feed_url("http://example.com/feed")


def test_market_ingest_is_idempotent_and_updates_changed_rows_in_place():
    with _make_session() as db:
        _seed_reference_data(db)
        submission = _submission(10)

        market.ingest(db, submission, commit=True)
        first_rows = db.query(market.MarketIndicator).all()
        assert len(first_rows) == 1
        assert first_rows[0].value == 10

        market.ingest(db, submission, commit=True)
        duplicate_rows = db.query(market.MarketIndicator).all()
        assert len(duplicate_rows) == 1
        assert duplicate_rows[0].value == 10

        market.ingest(db, _submission(12), commit=True)
        updated_rows = db.query(market.MarketIndicator).all()
        assert len(updated_rows) == 1
        assert updated_rows[0].value == 12
