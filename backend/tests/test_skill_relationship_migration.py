import importlib.util
from pathlib import Path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text


def test_curated_skill_relationship_migration_creates_and_seeds_edges() -> None:
    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "0034_curated_skill_relationships.py"
    )
    spec = importlib.util.spec_from_file_location(
        "curated_skill_relationships_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE skills_catalogue "
                "(id VARCHAR(36) PRIMARY KEY, canonical_name_fr VARCHAR(120) UNIQUE)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO skills_catalogue (id, canonical_name_fr) VALUES "
                "('python', 'Python'), ('excel', 'Excel'), "
                "('power-bi', 'Power BI'), ('sql', 'SQL'), "
                "('data-analysis', 'Data Analysis')"
            )
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        edges = connection.execute(
            text(
                "SELECT source, relation_type, strength, confidence "
                "FROM skill_relationships ORDER BY relation_type, strength"
            )
        ).all()
        assert len(edges) == 4
        assert {edge.source for edge in edges} == {"initial_curated_taxonomy"}
        assert {edge.relation_type for edge in edges} == {
            "RELATED_TO",
            "FOUNDATION_OF",
        }

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert "skill_relationships" not in inspect(connection).get_table_names()

    engine.dispose()
