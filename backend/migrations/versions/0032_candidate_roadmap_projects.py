"""Track candidate practical projects for roadmap skills."""

from alembic import op
import sqlalchemy as sa


revision = "0032_candidate_roadmap_projects"
down_revision = "0031_candidate_roadmap_goals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_roadmap_projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("skill_key", sa.String(length=60), nullable=False),
        sa.Column("skill", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=3000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned', 'in_progress', 'submitted')",
            name="ck_candidate_roadmap_projects_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_roadmap_projects_user_skill",
        "candidate_roadmap_projects",
        ["user_id", "skill_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_roadmap_projects_user_skill",
        table_name="candidate_roadmap_projects",
    )
    op.drop_table("candidate_roadmap_projects")
