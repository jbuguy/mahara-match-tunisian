"""Add structured candidate education and experience entries."""

from alembic import op
import sqlalchemy as sa

revision = "0012_structured_candidate_profiles"
down_revision = "0011_organisation_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("education_entries", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("candidate_profiles", sa.Column("experience_entries", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("candidate_profiles", "experience_entries")
    op.drop_column("candidate_profiles", "education_entries")
