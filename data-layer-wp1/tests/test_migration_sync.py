"""The SQL migration and the ORM are written by hand; these tests keep them identical.

The migration is parsed with pglast (the actual Postgres parser), so a syntax
error in the SQL also fails here.
"""

import enum
import re
from pathlib import Path

import pytest
from pglast import ast, parse_sql
from pglast.enums import ConstrType
from sqlalchemy import Enum as SAEnum

from mahara_data import enums
from mahara_data.db import Base
from mahara_data.reference import GOVERNORATES

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
MIGRATIONS = (
    MIGRATIONS_DIR / "20260921000000_wp1_shared_schema.sql",
    MIGRATIONS_DIR / "20261005000000_platform_auth_extensions.sql",
)
SQL = "\n".join(path.read_text(encoding="utf-8") for path in MIGRATIONS)


def _parse():
    tables: dict[str, dict[str, dict]] = {}
    enum_types: dict[str, list[str]] = {}
    seeds: dict[str, list[tuple]] = {}

    def column_info(col: ast.ColumnDef) -> dict:
        info = {"not_null": False, "fk": None}
        for c in col.constraints or ():
            if c.contype in (ConstrType.CONSTR_NOTNULL, ConstrType.CONSTR_PRIMARY):
                info["not_null"] = True
            elif c.contype == ConstrType.CONSTR_FOREIGN:
                info["fk"] = f"{c.pktable.relname}.{c.pk_attrs[0].sval}"
        return info

    for raw in parse_sql(SQL):
        stmt = raw.stmt
        if isinstance(stmt, ast.CreateEnumStmt):
            enum_types[stmt.typeName[-1].sval] = [v.sval for v in stmt.vals]
        elif isinstance(stmt, ast.CreateStmt):
            cols: dict[str, dict] = {}
            for elt in stmt.tableElts:
                if isinstance(elt, ast.ColumnDef):
                    cols[elt.colname] = column_info(elt)
                elif isinstance(elt, ast.Constraint) and elt.contype == ConstrType.CONSTR_PRIMARY:
                    for key in elt.keys:
                        cols[key.sval]["not_null"] = True
            tables[stmt.relation.relname] = cols
        elif isinstance(stmt, ast.AlterTableStmt):
            for cmd in stmt.cmds:
                if isinstance(cmd.def_, ast.ColumnDef):
                    tables[stmt.relation.relname][cmd.def_.colname] = column_info(cmd.def_)
        elif isinstance(stmt, ast.InsertStmt):
            rows = [tuple(v.val.sval for v in row) for row in stmt.selectStmt.valuesLists]
            seeds[stmt.relation.relname] = rows

    # company_size is created inside a DO block (idempotent for WP4 compatibility).
    match = re.search(r"create type public\.company_size as enum \(([^)]*)\)", SQL)
    enum_types["company_size"] = re.findall(r"'([^']*)'", match.group(1))
    return tables, enum_types, seeds


SQL_TABLES, SQL_ENUMS, SQL_SEEDS = _parse()
ORM_TABLES = Base.metadata.tables


def test_same_tables():
    assert set(SQL_TABLES) == set(ORM_TABLES)


@pytest.mark.parametrize("table_name", sorted(ORM_TABLES))
def test_same_columns_nullability_and_foreign_keys(table_name):
    orm_table = ORM_TABLES[table_name]
    sql_columns = SQL_TABLES[table_name]
    assert set(sql_columns) == set(orm_table.columns.keys())
    for column in orm_table.columns:
        sql = sql_columns[column.name]
        assert sql["not_null"] == (not column.nullable), f"{table_name}.{column.name} nullability differs"
        orm_fk = next(iter(column.foreign_keys), None)
        orm_target = f"{orm_fk.column.table.name}.{orm_fk.column.name}" if orm_fk else None
        assert sql["fk"] == orm_target, f"{table_name}.{column.name} foreign key differs"


def test_enum_types_match_python_enums():
    orm_enum_types = {
        column.type.name: column.type.enum_class
        for table in ORM_TABLES.values()
        for column in table.columns
        if isinstance(column.type, SAEnum)
    }
    assert set(SQL_ENUMS) == set(orm_enum_types)
    for name, enum_class in orm_enum_types.items():
        assert SQL_ENUMS[name] == [m.value for m in enum_class], f"enum {name} differs"


def test_every_python_enum_is_used():
    declared = {
        obj for obj in vars(enums).values() if isinstance(obj, type) and issubclass(obj, enum.Enum) and obj.__module__ == enums.__name__
    }
    used = {c.type.enum_class for t in ORM_TABLES.values() for c in t.columns if isinstance(c.type, SAEnum)}
    assert declared == used


def test_governorate_seed_matches_reference():
    assert SQL_SEEDS["governorates"] == [(code, fr, ar) for code, (fr, ar) in GOVERNORATES.items()]
    assert len(GOVERNORATES) == 24


def test_rls_enabled_on_every_table():
    block = SQL[SQL.index("Row Level Security") :]
    block = block[: block.index("] loop")]
    rls_tables = set(re.findall(r"'([a-z_]+)'", block))
    rls_tables.update(re.findall(r"alter table public\.([a-z_]+) enable row level security", SQL, re.IGNORECASE))
    assert rls_tables == set(ORM_TABLES)


def test_updated_at_trigger_on_every_table_with_updated_at():
    block = SQL[SQL.index("create or replace function public.set_updated_at") :]
    block = block[block.index("foreach") : block.index("] loop")]
    expected = {name for name, table in ORM_TABLES.items() if "updated_at" in table.columns}
    trigger_tables = set(re.findall(r"'([a-z_]+)'", block))
    trigger_tables.update(re.findall(r"create trigger ([a-z_]+)_set_updated_at", SQL, re.IGNORECASE))
    assert trigger_tables == expected
