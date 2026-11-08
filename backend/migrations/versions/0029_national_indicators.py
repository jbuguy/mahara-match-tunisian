"""Store parsed approved national indicator observations."""

from alembic import op
import sqlalchemy as sa


revision = "0029_national_indicators"
down_revision = "0028_admin_analytics_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "national_indicators",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("indicator_id", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("indicator_id", "year", name="uq_national_indicator_year"),
    )
    op.create_index("ix_national_indicators_indicator_id", "national_indicators", ["indicator_id"])


def downgrade() -> None:
    op.drop_index("ix_national_indicators_indicator_id", table_name="national_indicators")
    op.drop_table("national_indicators")
