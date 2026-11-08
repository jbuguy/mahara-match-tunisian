"""Add structured location fields to profiles and offerings."""

from alembic import op
import sqlalchemy as sa


revision = "0025_location_structured_fields"
down_revision = "0024_location_references"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("candidate_profiles", "job_offers", "training_courses"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("governorate_code", sa.String(80), nullable=True))
            batch_op.add_column(sa.Column("municipality_code", sa.String(120), nullable=True))
            batch_op.add_column(sa.Column("street_address", sa.String(200), nullable=True))


def downgrade() -> None:
    for table in ("training_courses", "job_offers", "candidate_profiles"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("street_address")
            batch_op.drop_column("municipality_code")
            batch_op.drop_column("governorate_code")
