from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import get_session
from app.main import app


@pytest.fixture
def migrated_location_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "locations.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


def test_location_reference_integrity(migrated_location_database) -> None:
    engine = migrated_location_database
    with engine.connect() as connection:
        governorate_count = connection.execute(
            text("SELECT COUNT(*) FROM governorates")
        ).scalar_one()
        assert governorate_count == 24

        invalid_governorates = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM municipalities AS m
                LEFT JOIN governorates AS g ON g.code = m.governorate_code
                WHERE g.code IS NULL
                """
            )
        ).scalar_one()
        assert invalid_governorates == 0

        duplicate_codes = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                    SELECT code FROM municipalities GROUP BY code HAVING COUNT(*) > 1
                )
                """
            )
        ).scalar_one()
        assert duplicate_codes == 0

        duplicate_names = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM (
                    SELECT governorate_code, LOWER(name_fr)
                    FROM municipalities
                    GROUP BY governorate_code, LOWER(name_fr)
                    HAVING COUNT(*) > 1
                )
                """
            )
        ).scalar_one()
        assert duplicate_names == 0

        governorates_without_options = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM governorates AS g
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM municipalities AS m
                    WHERE m.governorate_code = g.code
                )
                """
            )
        ).scalar_one()
        assert governorates_without_options == 0


def test_location_public_endpoints(migrated_location_database) -> None:
    engine = migrated_location_database

    def override_session():
        with Session(engine) as database:
            yield database

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            governorates = client.get("/locations/governorates")
            assert governorates.status_code == 200
            assert len(governorates.json()) == 24
            governorate_code = governorates.json()[0]["code"]
            municipalities = client.get(
                f"/locations/governorates/{governorate_code}/municipalities"
            )
            assert municipalities.status_code == 200
            assert municipalities.json()
            assert any(item["name_fr"] == "Autre / zone rurale" for item in municipalities.json())
            assert client.get("/locations/governorates/unknown/municipalities").status_code == 404
            assert "max-age" in governorates.headers["cache-control"]
    finally:
        app.dependency_overrides.clear()
