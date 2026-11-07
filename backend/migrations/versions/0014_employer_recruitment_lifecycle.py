"""Add employer recruitment lifecycle and collaboration records."""

from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision = "0014_employer_recruitment_lifecycle"
down_revision = "0013_organisation_context"
branch_labels = None
depends_on = None


APPLICATION_STATUSES = (
    "submitted",
    "reviewing",
    "shortlisted",
    "interview",
    "interview_completed",
    "offer_made",
    "hired",
    "rejected",
    "withdrawn",
)


def upgrade() -> None:
    op.add_column(
        "organisations",
        sa.Column(
            "verification_status",
            sa.Enum(
                "unverified", "pending", "verified", "rejected",
                name="organisation_verification_status", native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
            server_default="unverified",
        ),
    )
    op.add_column(
        "organisation_memberships",
        sa.Column(
            "role",
            sa.Enum(
                "owner", "administrator", "recruiter", "viewer",
                name="organisation_member_role", native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
            server_default="owner",
        ),
    )

    for column in (
        sa.Column("preferred_skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("employment_type", sa.String(length=40), nullable=True),
        sa.Column("workplace_arrangement", sa.String(length=20), nullable=True),
        sa.Column("positions_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "published", "paused", "closed", "expired", "archived",
                name="job_offer_status", native_enum=False, create_constraint=False,
            ),
            nullable=False,
            server_default="published",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    ):
        op.add_column("job_offers", column)
    op.execute("UPDATE job_offers SET published_at = created_at WHERE published_at IS NULL")

    with op.batch_alter_table("job_applications", recreate="always") as batch:
        batch.drop_constraint("job_application_status", type_="check")
        batch.alter_column(
            "status",
            existing_type=sa.Enum(
                "submitted", "reviewing", "interview", "hired", "rejected",
                name="job_application_status", native_enum=False,
            ),
            type_=sa.Enum(
                *APPLICATION_STATUSES,
                name="job_application_status", native_enum=False,
                create_constraint=True,
            ),
            existing_nullable=False,
        )

    op.create_table(
        "job_application_status_history",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_status_history_application_created",
        "job_application_status_history", ["application_id", "created_at"],
    )
    connection = op.get_bind()
    for application in connection.execute(
        sa.text("SELECT id, status, created_at FROM job_applications")
    ).fetchall():
        connection.execute(
            sa.text(
                "INSERT INTO job_application_status_history "
                "(id, application_id, actor_id, from_status, to_status, created_at) "
                "VALUES (:id, :application_id, NULL, NULL, :status, :created_at)"
            ),
            {
                "id": str(uuid4()),
                "application_id": application.id,
                "status": application.status,
                "created_at": application.created_at,
            },
        )

    op.create_table(
        "application_notes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("author_id", sa.String(36), nullable=True),
        sa.Column("content", sa.String(10000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_application_notes_application_created", "application_notes", ["application_id", "created_at"])

    op.create_table(
        "application_evaluations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("evaluator_id", sa.String(36), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.String(5000), nullable=True),
        sa.Column("concerns", sa.String(5000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluator_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "evaluator_id", name="uq_application_evaluation_evaluator"),
    )

    op.create_table(
        "talent_pools",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("employer_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employer_id", "name", name="uq_talent_pool_employer_name"),
    )
    op.create_table(
        "talent_pool_members",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("pool_id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("private_note", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["talent_pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "candidate_id", name="uq_talent_pool_candidate"),
    )

    op.create_table(
        "employer_conversations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_employer_conversation_application"),
    )
    op.create_table(
        "employer_messages",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("sender_id", sa.String(36), nullable=False),
        sa.Column("content", sa.String(10000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["employer_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employer_messages_conversation_created", "employer_messages", ["conversation_id", "created_at"])

    op.create_table(
        "employer_interviews",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("meeting_details", sa.String(2000), nullable=True),
        sa.Column("status", sa.Enum("proposed", "confirmed", "completed", "cancelled", "no_show", name="interview_status", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("feedback", sa.String(10000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employer_interviews_application_start", "employer_interviews", ["application_id", "starts_at"])

    op.create_table(
        "employer_interview_participants",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("interview_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["employer_interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", "user_id", name="uq_interview_participant_user"),
    )
    op.create_table(
        "employer_interview_feedback",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("interview_id", sa.String(36), nullable=False),
        sa.Column("author_id", sa.String(36), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.String(1000), nullable=True),
        sa.Column("notes", sa.String(10000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["employer_interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", "author_id", name="uq_interview_feedback_author"),
    )

    op.create_table(
        "job_offer_decisions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("application_id", sa.String(36), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposed_conditions", sa.JSON(), nullable=False),
        sa.Column("status", sa.Enum("pending", "accepted", "declined", "expired", "withdrawn", name="job_offer_decision_status", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_job_offer_decision_application"),
    )

    op.create_table(
        "employer_notifications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(1000), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employer_notifications_user_created", "employer_notifications", ["user_id", "created_at"])


def downgrade() -> None:
    for table, index in (
        ("employer_notifications", "ix_employer_notifications_user_created"),
        ("employer_interviews", "ix_employer_interviews_application_start"),
        ("employer_messages", "ix_employer_messages_conversation_created"),
        ("application_notes", "ix_application_notes_application_created"),
        ("job_application_status_history", "ix_application_status_history_application_created"),
    ):
        op.drop_index(index, table_name=table)
    for table in (
        "employer_notifications", "job_offer_decisions",
        "employer_interview_feedback", "employer_interview_participants",
        "employer_interviews",
        "employer_messages", "employer_conversations", "talent_pool_members",
        "talent_pools", "application_evaluations", "application_notes",
        "job_application_status_history",
    ):
        op.drop_table(table)
    op.execute("UPDATE job_applications SET status = 'reviewing' WHERE status = 'shortlisted'")
    op.execute("UPDATE job_applications SET status = 'interview' WHERE status IN ('interview_completed', 'offer_made')")
    op.execute("UPDATE job_applications SET status = 'rejected' WHERE status = 'withdrawn'")
    with op.batch_alter_table("job_applications", recreate="always") as batch:
        batch.drop_constraint("job_application_status", type_="check")
        batch.alter_column(
            "status",
            existing_type=sa.Enum(*APPLICATION_STATUSES, name="job_application_status", native_enum=False),
            type_=sa.Enum("submitted", "reviewing", "interview", "hired", "rejected", name="job_application_status", native_enum=False, create_constraint=True),
            existing_nullable=False,
        )
    op.drop_column("job_offers", "published_at")
    op.drop_column("job_offers", "status")
    op.drop_column("job_offers", "application_deadline")
    op.drop_column("job_offers", "salary_max")
    op.drop_column("job_offers", "salary_min")
    op.drop_column("job_offers", "positions_count")
    op.drop_column("job_offers", "workplace_arrangement")
    op.drop_column("job_offers", "employment_type")
    op.drop_column("job_offers", "preferred_skills")
    op.drop_column("organisation_memberships", "role")
    op.drop_column("organisations", "verification_status")
