"""Store private candidate learning project files and extracted text."""

from alembic import op
import sqlalchemy as sa


revision = "0038_candidate_learning_documents"
down_revision = "0037_candidate_learning_milestones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_learning_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("learning_project_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("processing_status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "processing_status IN ('completed', 'failed')",
            name="ck_candidate_learning_documents_status",
        ),
        sa.ForeignKeyConstraint(["learning_project_id"], ["candidate_learning_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_learning_documents_project_created",
        "candidate_learning_documents",
        ["learning_project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_learning_documents_project_created", table_name="candidate_learning_documents")
    op.drop_table("candidate_learning_documents")
