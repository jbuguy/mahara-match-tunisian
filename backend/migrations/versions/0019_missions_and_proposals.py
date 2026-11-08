"""Add independent missions, proposals, and mission status history."""

from alembic import op
import sqlalchemy as sa


revision = "0019_missions_and_proposals"
down_revision = "0018_professional_portfolios_service_area"
branch_labels = None
depends_on = None


def upgrade() -> None:
    mission_status = sa.Enum("draft", "published", "in_progress", "completed", "cancelled", "expired", "archived", name="mission_status", native_enum=False, create_constraint=True)
    proposal_status = sa.Enum("submitted", "under_review", "accepted", "rejected", "withdrawn", name="mission_proposal_status", native_enum=False, create_constraint=True)
    op.create_table(
        "missions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("publisher_user_id", sa.String(36), nullable=False),
        sa.Column("organisation_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("work_mode", sa.String(30), nullable=False),
        sa.Column("budget_type", sa.String(30), nullable=False),
        sa.Column("budget_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("budget_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("expected_start_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("duration", sa.String(120), nullable=True),
        sa.Column("workers_needed", sa.Integer(), nullable=False),
        sa.Column("status", mission_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("work_mode IN ('remote', 'on_site', 'hybrid', 'flexible')", name="ck_missions_work_mode"),
        sa.CheckConstraint("budget_type IN ('fixed', 'hourly', 'starting_at', 'quote', 'negotiable')", name="ck_missions_budget_type"),
        sa.CheckConstraint("budget_min IS NULL OR budget_min >= 0", name="ck_missions_budget_min_nonnegative"),
        sa.CheckConstraint("budget_max IS NULL OR budget_max >= 0", name="ck_missions_budget_max_nonnegative"),
        sa.CheckConstraint("budget_min IS NULL OR budget_max IS NULL OR budget_max >= budget_min", name="ck_missions_budget_range"),
        sa.CheckConstraint("workers_needed >= 1", name="ck_missions_workers_positive"),
        sa.ForeignKeyConstraint(["publisher_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_missions_status_created", "missions", ["status", "created_at"])
    op.create_index("ix_missions_publisher_created", "missions", ["publisher_user_id", "created_at"])
    op.create_index("ix_missions_organisation_status", "missions", ["organisation_id", "status"])
    op.create_table(
        "mission_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mission_id", sa.String(36), nullable=False),
        sa.Column("provider_user_id", sa.String(36), nullable=False),
        sa.Column("message", sa.String(5000), nullable=False),
        sa.Column("proposed_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_duration", sa.String(120), nullable=True),
        sa.Column("portfolio_references", sa.JSON(), nullable=False),
        sa.Column("availability", sa.String(1000), nullable=True),
        sa.Column("status", proposal_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mission_id", "provider_user_id", name="uq_mission_proposal_provider"),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_mission_proposals_mission_status", "mission_proposals", ["mission_id", "status"])
    op.create_index("ix_mission_proposals_provider_created", "mission_proposals", ["provider_user_id", "created_at"])
    op.create_table(
        "mission_status_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mission_id", sa.String(36), nullable=False),
        sa.Column("changed_by_user_id", sa.String(36), nullable=True),
        sa.Column("previous_status", sa.Enum("draft", "published", "in_progress", "completed", "cancelled", "expired", "archived", name="mission_history_previous_status", native_enum=False, create_constraint=False), nullable=True),
        sa.Column("new_status", sa.Enum("draft", "published", "in_progress", "completed", "cancelled", "expired", "archived", name="mission_history_new_status", native_enum=False, create_constraint=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_mission_status_history_mission_created", "mission_status_history", ["mission_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_mission_status_history_mission_created", table_name="mission_status_history")
    op.drop_table("mission_status_history")
    op.drop_index("ix_mission_proposals_provider_created", table_name="mission_proposals")
    op.drop_index("ix_mission_proposals_mission_status", table_name="mission_proposals")
    op.drop_table("mission_proposals")
    op.drop_index("ix_missions_organisation_status", table_name="missions")
    op.drop_index("ix_missions_publisher_created", table_name="missions")
    op.drop_index("ix_missions_status_created", table_name="missions")
    op.drop_table("missions")
