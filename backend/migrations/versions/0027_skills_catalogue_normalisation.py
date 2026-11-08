"""Add canonical skills catalogue, normalized links, and unmatched review queue."""

import json
import re
from pathlib import Path
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0027_skills_catalogue_normalisation"
down_revision = "0026_lifecycle_analytics_fields"
branch_labels = None
depends_on = None


def _key(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9\u00c0-\u024f]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def upgrade() -> None:
    op.create_table(
        "skills_catalogue",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("canonical_name_fr", sa.String(length=120), nullable=False),
        sa.Column("canonical_name_en", sa.String(length=120), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_name_fr"),
        sa.UniqueConstraint("canonical_name_en"),
    )
    op.create_table(
        "candidate_skills",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills_catalogue.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "skill_id"),
    )
    op.create_table(
        "offer_skills",
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("skill_type", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["job_offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills_catalogue.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("offer_id", "skill_id", "skill_type"),
    )
    op.create_table(
        "course_skills",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["training_courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills_catalogue.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("course_id", "skill_id"),
    )
    op.create_table(
        "skill_alias_review",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("raw_skill", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    seed_path = Path(__file__).resolve().parents[2] / "data" / "skills_catalogue.json"
    with seed_path.open("r", encoding="utf-8") as stream:
        seed = json.load(stream)

    connection = op.get_bind()
    aliases_by_key = {}
    for canonical_fr, values in seed.items():
        skill_id = canonical_fr.casefold().replace("/", "-")
        skill_id = re.sub(r"[^a-z0-9]+", "-", skill_id).strip("-")
        aliases = list(dict.fromkeys([canonical_fr, values["canonical_name_en"], *values["aliases"]]))
        connection.execute(
            sa.text(
                "INSERT INTO skills_catalogue "
                "(id, canonical_name_fr, canonical_name_en, aliases) "
                "VALUES (:id, :fr, :en, :aliases)"
            ),
            {"id": skill_id, "fr": canonical_fr, "en": values["canonical_name_en"], "aliases": json.dumps(aliases)},
        )
        for alias in aliases:
            aliases_by_key[_key(alias)] = skill_id

    def raw_values(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.keys())
        return []

    def backfill(table, id_column, raw_column, entity_type, link_table):
        rows = connection.execute(
            sa.text(f"SELECT {id_column}, {raw_column} FROM {table}")
        )
        for row in rows:
            raw = getattr(row, raw_column)
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except json.JSONDecodeError:
                    raw = []
            raw = raw_values(raw)
            for value in dict.fromkeys(str(item).strip() for item in raw if str(item).strip()):
                skill_id = aliases_by_key.get(_key(value))
                if skill_id:
                    connection.execute(
                        sa.text(f"INSERT INTO {link_table} "
                                f"({id_column}, skill_id) VALUES (:entity_id, :skill_id) "
                                "ON CONFLICT DO NOTHING"),
                        {"entity_id": getattr(row, id_column), "skill_id": skill_id},
                    )
                else:
                    connection.execute(
                        sa.text(
                            "INSERT INTO skill_alias_review "
                            "(id, entity_type, entity_id, raw_skill) VALUES (:id, :type, :entity_id, :raw)"
                        ),
                        {"id": str(uuid4()), "type": entity_type, "entity_id": getattr(row, id_column), "raw": value[:120]},
                    )

    backfill("candidate_profiles", "user_id", "skills", "candidate", "candidate_skills")
    backfill("training_courses", "id", "skills", "course", "course_skills")

    for skill_type in ("required", "preferred"):
        rows = connection.execute(sa.text(f"SELECT id, {skill_type}_skills FROM job_offers"))
        for row in rows:
            raw = row[1]
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except json.JSONDecodeError:
                    raw = []
            for value in dict.fromkeys(str(item).strip() for item in raw_values(raw) if str(item).strip()):
                skill_id = aliases_by_key.get(_key(value))
                if skill_id:
                    connection.execute(
                        sa.text(
                            "INSERT INTO offer_skills (offer_id, skill_id, skill_type) "
                            "VALUES (:offer_id, :skill_id, :skill_type) ON CONFLICT DO NOTHING"
                        ),
                        {"offer_id": row[0], "skill_id": skill_id, "skill_type": skill_type},
                    )
                else:
                    connection.execute(
                        sa.text(
                            "INSERT INTO skill_alias_review "
                            "(id, entity_type, entity_id, raw_skill) VALUES (:id, :type, :entity_id, :raw)"
                        ),
                        {"id": str(uuid4()), "type": f"offer:{skill_type}", "entity_id": row[0], "raw": value[:120]},
                    )


def downgrade() -> None:
    op.drop_table("skill_alias_review")
    op.drop_table("course_skills")
    op.drop_table("offer_skills")
    op.drop_table("candidate_skills")
    op.drop_table("skills_catalogue")
