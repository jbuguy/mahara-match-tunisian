"""Add candidate-owned learning projects and scope assistant sessions to them."""

from alembic import op
import sqlalchemy as sa


revision = "0036_candidate_learning_projects"
down_revision = "0035_professional_public_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_learning_projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("objective", sa.String(length=2000), nullable=False),
        sa.Column("target_profession", sa.String(length=160), nullable=True),
        sa.Column("starting_level", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_candidate_learning_projects_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidate_learning_projects_user_status", "candidate_learning_projects", ["user_id", "status"])
    with op.batch_alter_table("candidate_assistant_sessions") as batch_op:
        batch_op.add_column(sa.Column("learning_project_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_candidate_assistant_sessions_learning_project",
            "candidate_learning_projects",
            ["learning_project_id"],
            ["id"],
            ondelete="CASCADE",
        )
    op.create_index("ix_candidate_assistant_sessions_project_updated", "candidate_assistant_sessions", ["learning_project_id", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_candidate_assistant_sessions_project_updated", table_name="candidate_assistant_sessions")
    with op.batch_alter_table("candidate_assistant_sessions") as batch_op:
        batch_op.drop_constraint("fk_candidate_assistant_sessions_learning_project", type_="foreignkey")
        batch_op.drop_column("learning_project_id")
    op.drop_index("ix_candidate_learning_projects_user_status", table_name="candidate_learning_projects")
    op.drop_table("candidate_learning_projects")
