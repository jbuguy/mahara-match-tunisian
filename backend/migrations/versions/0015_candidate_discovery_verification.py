"""Add candidate discovery consent and organisation verification requests."""

from alembic import op
import sqlalchemy as sa

revision = "0015_candidate_discovery_verification"
down_revision = "0014_employer_recruitment_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("professional_headline", sa.String(200), nullable=True))
    op.add_column(
        "candidate_profiles",
        sa.Column("employer_discoverable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "organisation_verification_requests",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organisation_id", sa.String(36), nullable=False),
        sa.Column("submitted_by", sa.String(36), nullable=True),
        sa.Column("supporting_information", sa.String(4000), nullable=False),
        sa.Column("evidence_url", sa.String(1000), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "unverified", "pending", "verified", "rejected",
                name="verification_request_status", native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reviewer_note", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organisation_verification_status_created",
        "organisation_verification_requests",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organisation_verification_status_created",
        table_name="organisation_verification_requests",
    )
    op.drop_table("organisation_verification_requests")
    op.drop_column("candidate_profiles", "employer_discoverable")
    op.drop_column("candidate_profiles", "professional_headline")
