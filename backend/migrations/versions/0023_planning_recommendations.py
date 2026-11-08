"""Add planning documents, recommendations and offer links."""

from alembic import op
import sqlalchemy as sa


revision = "0023_planning_recommendations"
down_revision = "0022_planning_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employer_planning_documents",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("planning_session_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["planning_session_id"], ["employer_planning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_planning_documents_session_created", "employer_planning_documents", ["planning_session_id", "created_at"])
    op.create_table(
        "employer_planning_recommendations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("planning_session_id", sa.String(36), nullable=False),
        sa.Column("recommendation_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["planning_session_id"], ["employer_planning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_planning_recommendations_session_created", "employer_planning_recommendations", ["planning_session_id", "created_at"])
    with op.batch_alter_table("job_offers") as batch_op:
        batch_op.add_column(sa.Column("planning_session_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("planning_recommendation_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key(
            "fk_job_offers_planning_session",
            "employer_planning_sessions",
            ["planning_session_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_job_offers_planning_recommendation",
            "employer_planning_recommendations",
            ["planning_recommendation_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("job_offers") as batch_op:
        batch_op.drop_constraint("fk_job_offers_planning_recommendation", type_="foreignkey")
        batch_op.drop_constraint("fk_job_offers_planning_session", type_="foreignkey")
        batch_op.drop_column("planning_recommendation_id")
        batch_op.drop_column("planning_session_id")
    op.drop_index("ix_planning_recommendations_session_created", table_name="employer_planning_recommendations")
    op.drop_table("employer_planning_recommendations")
    op.drop_index("ix_planning_documents_session_created", table_name="employer_planning_documents")
    op.drop_table("employer_planning_documents")
