from contextlib import nullcontext
from pathlib import Path

import pytest

from app.migrate import (
    LEGACY_BASELINE_VERSIONS,
    LEGACY_REQUIRED_COLUMNS,
    ROOT_MIGRATIONS_DIR,
    Migration,
    MigrationError,
    _legacy_table_names,
    apply_migrations,
    discover_migrations,
)


class FakeResult:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, *, existing_schema=False, schema_rows=(), vector=True):
        self.existing_schema = existing_schema
        self.schema_rows = list(schema_rows)
        self.vector = vector
        self.records = {}
        self.sql_statements = []

    def transaction(self):
        return nullcontext()

    def execute(self, query, params=None, *, prepare=None):
        normalized = " ".join(query.lower().split())
        if "to_regclass('public.users')" in normalized:
            values = ("users", "employers", None) if self.existing_schema else (None, None, None)
            return FakeResult([values])
        if "from information_schema.columns" in normalized:
            return FakeResult(self.schema_rows)
        if "from pg_extension" in normalized:
            return FakeResult([(self.vector,)])
        if normalized.startswith("select version, filename, checksum"):
            return FakeResult(
                [(version, filename, checksum) for version, (filename, checksum) in sorted(self.records.items())]
            )
        if normalized.startswith("insert into public.platform_schema_migrations"):
            version, filename, checksum = params
            self.records[version] = (filename, checksum)
            return FakeResult()
        if prepare is False:
            self.sql_statements.append(query)
        return FakeResult()


def write_migration(directory: Path, filename: str, sql: str) -> Path:
    path = directory / filename
    path.write_text(sql, encoding="utf-8")
    return path


def migration(version: str, filename: str, sql: str) -> Migration:
    from hashlib import sha256

    return Migration(version, filename, sha256(sql.encode()).hexdigest(), sql)


def test_discover_migrations_sorts_and_hashes_sql(tmp_path):
    newer = write_migration(tmp_path, "20260922000000_second.sql", "select 2;")
    older = write_migration(tmp_path, "20260920000000_first.sql", "select 1;")

    found = discover_migrations(tmp_path)

    assert [item.filename for item in found] == [older.name, newer.name]
    assert found[0].sql == "select 1;"
    assert len(found[0].checksum) == 64


def test_discover_rejects_invalid_and_duplicate_versions(tmp_path):
    write_migration(tmp_path, "bad-name.sql", "select 1;")
    with pytest.raises(MigrationError, match="Invalid migration filename"):
        discover_migrations(tmp_path)

    (tmp_path / "bad-name.sql").unlink()
    write_migration(tmp_path, "20260920000000_first.sql", "select 1;")
    write_migration(tmp_path, "20260920000000_second.sql", "select 2;")
    with pytest.raises(MigrationError, match="Duplicate migration version"):
        discover_migrations(tmp_path)


def test_apply_tracks_each_migration_and_is_idempotent():
    migrations = [
        migration("20260920000000", "20260920000000_first.sql", "select 1;"),
        migration("20260921000000", "20260921000000_second.sql", "select 2;"),
    ]
    connection = FakeConnection()

    first = apply_migrations(connection, migrations)
    second = apply_migrations(connection, migrations)

    assert first.applied_versions == ("20260920000000", "20260921000000")
    assert second.applied_versions == ()
    assert list(connection.records) == ["20260920000000", "20260921000000"]
    assert connection.sql_statements == ["select 1;", "select 2;"]


def test_applied_migration_checksum_must_not_change():
    original = migration("20260920000000", "20260920000000_first.sql", "select 1;")
    changed = migration("20260920000000", "20260920000000_first.sql", "select 2;")
    connection = FakeConnection()
    apply_migrations(connection, [original])

    with pytest.raises(MigrationError, match="Applied migration has changed"):
        apply_migrations(connection, [changed])


def test_existing_schema_requires_explicit_baseline():
    migration_item = migration("20260920000000", "20260920000000_first.sql", "select 1;")

    with pytest.raises(MigrationError, match="--baseline-existing"):
        apply_migrations(FakeConnection(existing_schema=True), [migration_item])


def test_baseline_validates_wp1_schema_then_applies_new_migrations(tmp_path):
    migrations = discover_migrations(ROOT_MIGRATIONS_DIR)
    migrations.append(migration("20261006000000", "20261006000000_new.sql", "select 2;"))
    schema = {
        (table, "id"): "text"
        for table in _legacy_table_names(migrations)
    }
    schema.update(
        {
            (table, column): (
                "user_role" if table == "users" and column == "role"
                else "company_size" if table == "employers" and column == "company_size"
                else "text"
            )
            for table, columns in LEGACY_REQUIRED_COLUMNS.items()
            for column in columns
        }
    )
    schema_rows = [(table, column, udt_name) for (table, column), udt_name in schema.items()]
    connection = FakeConnection(existing_schema=True, schema_rows=schema_rows)

    report = apply_migrations(connection, migrations, baseline_existing=True)

    assert report.baselined_versions == LEGACY_BASELINE_VERSIONS
    assert report.applied_versions == ("20261004010000", "20261005000000", "20261006000000")


def test_baseline_rejects_incomplete_legacy_schema():
    migrations = discover_migrations(ROOT_MIGRATIONS_DIR)
    connection = FakeConnection(existing_schema=True)

    with pytest.raises(MigrationError, match="does not match the migration baseline"):
        apply_migrations(connection, migrations, baseline_existing=True)