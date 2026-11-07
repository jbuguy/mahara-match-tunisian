"""Store structured employer context on the existing organisation record."""

from alembic import op
import sqlalchemy as sa

revision = "0013_organisation_context"
down_revision = "0012_structured_candidate_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organisations",
        sa.Column("profile_details", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("organisations", "profile_details")
