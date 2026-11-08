"""Add Tunisian governorate and municipality reference data."""

import csv
from pathlib import Path

from alembic import op
import sqlalchemy as sa


revision = "0024_location_references"
down_revision = "0023_planning_recommendations"
branch_labels = None
depends_on = None


def _data_file(filename: str) -> Path:
    return Path(__file__).parents[2] / "data" / "location" / filename


def upgrade() -> None:
    op.create_table(
        "governorates",
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name_fr", sa.String(120), nullable=False),
        sa.Column("name_ar", sa.String(120), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "municipalities",
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("governorate_code", sa.String(80), nullable=False),
        sa.Column("name_fr", sa.String(160), nullable=False),
        sa.Column("name_ar", sa.String(160), nullable=False),
        sa.Column("delegation_name_fr", sa.String(160), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["governorate_code"],
            ["governorates.code"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("code"),
        sa.UniqueConstraint(
            "governorate_code",
            "name_fr",
            name="uq_municipality_governorate_name_fr",
        ),
    )
    op.create_index(
        "ix_municipalities_governorate_sort",
        "municipalities",
        ["governorate_code", "sort_order"],
    )

    governorates = sa.table(
        "governorates",
        sa.column("code", sa.String),
        sa.column("name_fr", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("latitude", sa.Float),
        sa.column("longitude", sa.Float),
    )
    municipalities = sa.table(
        "municipalities",
        sa.column("code", sa.String),
        sa.column("governorate_code", sa.String),
        sa.column("name_fr", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("delegation_name_fr", sa.String),
        sa.column("sort_order", sa.Integer),
    )

    with _data_file("governorates.csv").open(newline="", encoding="utf-8") as file:
        governorate_rows = [
            {
                **row,
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            }
            for row in csv.DictReader(file)
        ]
    op.bulk_insert(governorates, governorate_rows)

    with _data_file("municipalities.csv").open(newline="", encoding="utf-8") as file:
        municipality_rows = [
            {
                **row,
                "delegation_name_fr": row["delegation_name_fr"] or None,
                "sort_order": int(row["sort_order"]),
            }
            for row in csv.DictReader(file)
        ]
    op.bulk_insert(municipalities, municipality_rows)


def downgrade() -> None:
    op.drop_index(
        "ix_municipalities_governorate_sort",
        table_name="municipalities",
    )
    op.drop_table("municipalities")
    op.drop_table("governorates")
