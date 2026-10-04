"""Apply the repository's ordered SQL migrations with version and checksum tracking.

Run from ``backend`` with ``python -m app.migrate``. Existing databases without
tracking metadata require the explicit ``--baseline-existing`` option.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from sqlalchemy.engine import make_url

from .config import get_settings

MIGRATION_FILENAME = re.compile(r"^(?P<version>\d{14})_[a-z0-9_]+\.sql$")
MIGRATION_TABLE = "public.platform_schema_migrations"
MIGRATION_LOCK_ID = 8_675_309_123_456_789
LEGACY_BASELINE_VERSIONS = (
    "20260920000000",
    "20260921000000",
    "20260922000000",
)
ROOT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
CREATE_TABLE_PATTERN = re.compile(
    r"\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?([a-z_][a-z0-9_]*)\s*\(",
    re.IGNORECASE,
)
LEGACY_REQUIRED_COLUMNS = {
    "users": {
        "id", "role", "email", "phone", "password_hash", "preferred_language",
        "is_active", "last_login_at", "created_at", "updated_at",
    },
    "candidates": {
        "id", "user_id", "onboarding_path", "literacy_level", "governorate_code",
        "education_level", "years_experience", "languages", "summary", "available_from",
        "consent_version", "consent_given_at", "created_at", "updated_at",
    },
    "candidate_pii": {"candidate_id", "full_name", "email", "phone"},
    "employers": {
        "id", "user_id", "company_name", "email", "password_hash", "sector", "company_size",
        "created_at", "verified", "sector_id", "tax_id", "governorate_code", "website",
        "description", "updated_at",
    },
    "job_offers": {
        "id", "employer_id", "title", "description_raw", "occupation_id", "sector_id",
        "contract_type", "work_mode", "governorate_code", "positions_count", "min_years_experience",
        "education_level_min", "salary_min_tnd", "salary_max_tnd", "languages_required", "status",
        "source", "published_at", "expires_at", "created_at", "updated_at",
    },
    "job_offer_skills": {"job_offer_id", "skill_id", "requirement", "min_level"},
    "applications": {
        "id", "candidate_id", "job_offer_id", "match_result_id", "status", "cover_note",
        "applied_at", "updated_at",
    },
    "hiring_feedback": {
        "id", "application_id", "employer_id", "decision", "reason_code", "match_quality",
        "comment", "created_at",
    },
    "employer_draft_sessions": {
        "id", "employer_id", "state", "messages", "draft", "created_at", "updated_at",
    },
}


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    filename: str
    checksum: str
    sql: str


@dataclass(frozen=True)
class MigrationReport:
    applied_versions: tuple[str, ...]
    baselined_versions: tuple[str, ...]


def discover_migrations(directory: Path) -> list[Migration]:
    migrations = []
    versions = set()
    for path in sorted(directory.glob("*.sql")):
        match = MIGRATION_FILENAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {path.name}")
        version = match.group("version")
        if version in versions:
            raise MigrationError(f"Duplicate migration version: {version}")
        content = path.read_bytes()
        if not content.strip():
            raise MigrationError(f"Migration is empty: {path.name}")
        versions.add(version)
        migrations.append(
            Migration(
                version=version,
                filename=path.name,
                checksum=hashlib.sha256(content).hexdigest(),
                sql=content.decode("utf-8"),
            )
        )
    return migrations


def _has_legacy_schema(connection: Any) -> bool:
    row = connection.execute(
        """select to_regclass('public.users'),
                  to_regclass('public.employers'),
                  to_regclass('public.job_offers')"""
    ).fetchone()
    return any(value is not None for value in row)


def _legacy_table_names(migrations: list[Migration]) -> set[str]:
    baseline_sql = "\n".join(
        migration.sql for migration in migrations if migration.version in LEGACY_BASELINE_VERSIONS
    )
    return set(CREATE_TABLE_PATTERN.findall(baseline_sql))


def _verify_legacy_schema(connection: Any, migrations: list[Migration]) -> None:
    expected_tables = _legacy_table_names(migrations)
    expected_columns = LEGACY_REQUIRED_COLUMNS
    actual_columns: dict[str, set[str]] = {}
    actual_types: dict[tuple[str, str], str] = {}
    for table_name, column_name, udt_name in connection.execute(
        """select table_name, column_name, udt_name
           from information_schema.columns
           where table_schema = 'public'"""
    ).fetchall():
        actual_columns.setdefault(table_name, set()).add(column_name)
        actual_types[(table_name, column_name)] = udt_name

    missing_tables = expected_tables - actual_columns.keys()
    missing = []
    for table_name, columns in expected_columns.items():
        absent_columns = columns - actual_columns.get(table_name, set())
        if absent_columns:
            if table_name not in actual_columns:
                missing.append(f"table {table_name}")
            else:
                missing.append(f"{table_name}.{', '.join(sorted(absent_columns))}")

    wrong_types = {
        f"{table}.{column}": expected
        for (table, column), expected in {
            ("users", "role"): "user_role",
            ("employers", "company_size"): "company_size",
        }.items()
        if actual_types.get((table, column)) != expected
    }
    has_vector = connection.execute(
        "select exists(select 1 from pg_extension where extname = 'vector')"
    ).fetchone()[0]

    problems = []
    if missing_tables:
        problems.append("missing WP1 tables: " + ", ".join(sorted(missing_tables)))
    if missing:
        problems.append("missing WP1 schema objects: " + "; ".join(missing))
    if wrong_types:
        problems.append(
            "unexpected column types: "
            + "; ".join(f"{column} must use {expected}" for column, expected in wrong_types.items())
        )
    if not has_vector:
        problems.append("the pgvector extension is not installed")
    if problems:
        raise MigrationError("Existing schema does not match the migration baseline: " + " | ".join(problems))


def _record_migration(connection: Any, migration: Migration) -> None:
    connection.execute(
        f"""insert into {MIGRATION_TABLE} (version, filename, checksum)
            values (%s, %s, %s)""",
        (migration.version, migration.filename, migration.checksum),
    )


def apply_migrations(
    connection: Any,
    migrations: list[Migration],
    *,
    baseline_existing: bool = False,
) -> MigrationReport:
    if not migrations:
        raise MigrationError("No SQL migrations were found")

    lock_acquired = False
    applied_versions: list[str] = []
    baselined_versions: list[str] = []
    try:
        with connection.transaction():
            connection.execute("select pg_advisory_lock(%s)", (MIGRATION_LOCK_ID,))
        lock_acquired = True

        with connection.transaction():
            connection.execute(
                f"""create table if not exists {MIGRATION_TABLE} (
                    version varchar(14) primary key,
                    filename text not null unique,
                    checksum char(64) not null,
                    applied_at timestamptz not null default now()
                )"""
            )

        records = connection.execute(
            f"select version, filename, checksum from {MIGRATION_TABLE} order by version"
        ).fetchall()
        recorded = {version: (filename, checksum) for version, filename, checksum in records}
        migration_by_version = {migration.version: migration for migration in migrations}

        unknown_versions = set(recorded) - set(migration_by_version)
        if unknown_versions:
            raise MigrationError("Applied migration files are missing: " + ", ".join(sorted(unknown_versions)))
        for version, (filename, checksum) in recorded.items():
            migration = migration_by_version[version]
            if filename != migration.filename or checksum != migration.checksum:
                raise MigrationError(f"Applied migration has changed: {migration.filename}")

        if not recorded:
            has_legacy_schema = _has_legacy_schema(connection)
            if has_legacy_schema and not baseline_existing:
                raise MigrationError(
                    "Existing schema has no migration history; verify it, then rerun with --baseline-existing"
                )
            if baseline_existing:
                if not has_legacy_schema:
                    raise MigrationError("No existing schema was found to baseline")
                baseline = [
                    migration_by_version[version]
                    for version in LEGACY_BASELINE_VERSIONS
                    if version in migration_by_version
                ]
                if tuple(migration.version for migration in baseline) != LEGACY_BASELINE_VERSIONS:
                    raise MigrationError("The known legacy migration files are incomplete")
                _verify_legacy_schema(connection, baseline)
                with connection.transaction():
                    for migration in baseline:
                        _record_migration(connection, migration)
                        baselined_versions.append(migration.version)
                recorded.update(
                    {migration.version: (migration.filename, migration.checksum) for migration in baseline}
                )

        for migration in migrations:
            if migration.version in recorded:
                continue
            with connection.transaction():
                connection.execute(migration.sql, prepare=False)
                _record_migration(connection, migration)
            applied_versions.append(migration.version)
    finally:
        if lock_acquired:
            with connection.transaction():
                connection.execute("select pg_advisory_unlock(%s)", (MIGRATION_LOCK_ID,))

    return MigrationReport(tuple(applied_versions), tuple(baselined_versions))


def _database_dsn(value: str) -> str:
    url = make_url(value)
    if not url.drivername.startswith("postgresql"):
        raise MigrationError("Migrations require a PostgreSQL database URL")
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply versioned Mahara Match PostgreSQL migrations")
    parser.add_argument("--database-url", default=None, help="PostgreSQL URL (defaults to backend settings)")
    parser.add_argument("--migrations-dir", type=Path, default=ROOT_MIGRATIONS_DIR)
    parser.add_argument(
        "--baseline-existing",
        action="store_true",
        help="Verify and stamp the known legacy schema before applying newer migrations",
    )
    args = parser.parse_args(argv)

    try:
        migrations = discover_migrations(args.migrations_dir)
        database_url = args.database_url or get_settings().database_url
        with psycopg.connect(_database_dsn(database_url), autocommit=True) as connection:
            report = apply_migrations(connection, migrations, baseline_existing=args.baseline_existing)
    except (MigrationError, psycopg.Error, ValueError) as error:
        print(f"Migration failed: {error}", file=sys.stderr)
        return 1

    for version in report.baselined_versions:
        print(f"Verified and baselined {version}")
    for version in report.applied_versions:
        print(f"Applied {version}")
    if not report.baselined_versions and not report.applied_versions:
        print("Database schema is up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())