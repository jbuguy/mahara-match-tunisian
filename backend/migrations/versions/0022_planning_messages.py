"""Add organisation-scoped workforce planning conversations."""

from alembic import op
import sqlalchemy as sa


revision = "0022_planning_messages"
down_revision = "0021_employer_planning_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_planning_messages",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("planning_session_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["planning_session_id"],
            ["employer_planning_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_planning_messages_session_created",
        "employer_planning_messages",
        ["planning_session_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_planning_messages_session_created",
        table_name="employer_planning_messages",
    )
    op.drop_table("employer_planning_messages")
