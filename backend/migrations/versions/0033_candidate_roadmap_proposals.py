"""Store candidate-approved roadmap change proposals."""

from alembic import op
import sqlalchemy as sa


revision = "0033_candidate_roadmap_proposals"
down_revision = "0032_candidate_roadmap_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_roadmap_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("goal_type", sa.String(length=20), nullable=False),
        sa.Column("target_offer_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "goal_type IN ('target_job', 'skill_exploration')",
            name="ck_candidate_roadmap_proposals_goal_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_candidate_roadmap_proposals_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_offer_id"], ["job_offers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_roadmap_proposals_user_status",
        "candidate_roadmap_proposals",
        ["user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_roadmap_proposals_user_status",
        table_name="candidate_roadmap_proposals",
    )
    op.drop_table("candidate_roadmap_proposals")
