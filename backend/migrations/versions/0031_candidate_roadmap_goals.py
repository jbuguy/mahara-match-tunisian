"""Persist candidate-selected roadmap goals independently of assistant chats."""

from alembic import op
import sqlalchemy as sa


revision = "0031_candidate_roadmap_goals"
down_revision = "0030_bge_m3_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_roadmap_goals",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("goal_type", sa.String(length=20), nullable=False),
        sa.Column("target_offer_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "goal_type IN ('target_job', 'skill_exploration')",
            name="ck_candidate_roadmap_goals_type",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_offer_id"], ["job_offers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("candidate_roadmap_goals")
