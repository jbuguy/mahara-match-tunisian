"""Persist employer notification preferences."""

from alembic import op
import sqlalchemy as sa

revision = "0016_employer_notification_preferences"
down_revision = "0015_candidate_discovery_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_notification_preferences",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "notification_type"),
    )


def downgrade() -> None:
    op.drop_table("employer_notification_preferences")
