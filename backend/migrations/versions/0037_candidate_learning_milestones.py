"""Persist ordered milestones for each candidate learning project."""

from alembic import op
import sqlalchemy as sa


revision = "0037_candidate_learning_milestones"
down_revision = "0036_candidate_learning_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_learning_milestones",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("learning_project_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("skill", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed')",
            name="ck_candidate_learning_milestones_status",
        ),
        sa.ForeignKeyConstraint(["learning_project_id"], ["candidate_learning_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_learning_milestones_project_order",
        "candidate_learning_milestones",
        ["learning_project_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_learning_milestones_project_order", table_name="candidate_learning_milestones")
    op.drop_table("candidate_learning_milestones")
