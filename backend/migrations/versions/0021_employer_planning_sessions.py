"""Add organisation-scoped employer planning sessions."""

from alembic import op
import sqlalchemy as sa


revision = "0021_employer_planning_sessions"
down_revision = "0020_service_requests_and_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_planning_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organisation_id", sa.String(36), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("project_type", sa.String(40), nullable=False, server_default="other"),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "in_progress", "analysis_ready", "completed", "archived",
                name="planning_session_status", native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("project_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_planning_sessions_organisation_updated",
        "employer_planning_sessions",
        ["organisation_id", "updated_at"],
    )
    op.create_index(
        "ix_planning_sessions_created_by",
        "employer_planning_sessions",
        ["created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_planning_sessions_created_by", table_name="employer_planning_sessions")
    op.drop_index("ix_planning_sessions_organisation_updated", table_name="employer_planning_sessions")
    op.drop_table("employer_planning_sessions")
