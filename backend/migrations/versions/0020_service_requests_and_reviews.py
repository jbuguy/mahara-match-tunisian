"""Add service requests, issue reporting, and eligible interaction reviews."""

from alembic import op
import sqlalchemy as sa


revision = "0020_service_requests_and_reviews"
down_revision = "0019_missions_and_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service_id", sa.String(36), nullable=False),
        sa.Column("requester_user_id", sa.String(36), nullable=False),
        sa.Column("provider_user_id", sa.String(36), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("preferred_date", sa.Date(), nullable=True),
        sa.Column("budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=False),
        sa.Column("agreed_scope", sa.String(5000), nullable=True),
        sa.Column("report_reason", sa.String(2000), nullable=True),
        sa.Column("status", sa.Enum("requested", "accepted", "declined", "in_progress", "completion_requested", "completed", "cancelled", "disputed", name="service_request_status", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["service_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_service_requests_requester_created", "service_requests", ["requester_user_id", "created_at"])
    op.create_index("ix_service_requests_provider_status", "service_requests", ["provider_user_id", "status"])
    op.create_index("ix_service_requests_service_status", "service_requests", ["service_id", "status"])
    op.create_table(
        "service_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service_request_id", sa.String(36), nullable=False),
        sa.Column("reviewer_user_id", sa.String(36), nullable=False),
        sa.Column("provider_user_id", sa.String(36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("service_request_id", name="uq_service_review_request"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_service_reviews_rating_range"),
        sa.ForeignKeyConstraint(["service_request_id"], ["service_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_service_reviews_provider_created", "service_reviews", ["provider_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_service_reviews_provider_created", table_name="service_reviews")
    op.drop_table("service_reviews")
    op.drop_index("ix_service_requests_service_status", table_name="service_requests")
    op.drop_index("ix_service_requests_provider_status", table_name="service_requests")
    op.drop_index("ix_service_requests_requester_created", table_name="service_requests")
    op.drop_table("service_requests")
