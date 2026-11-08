"""Add application lifecycle and candidate analytics fields."""

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0026_lifecycle_analytics_fields"
down_revision = "0025_location_structured_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("birth_year", sa.Integer(), nullable=True))
    op.add_column("candidate_profiles", sa.Column("profile_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("candidate_profiles", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("course_enrollments", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    application_statuses = (
        "submitted", "reviewing", "shortlisted", "interview", "interview_completed",
        "offer_made", "interviewed", "offered", "hired", "rejected", "withdrawn",
    )
    with op.batch_alter_table("job_applications", recreate="never") as batch:
        batch.drop_constraint("job_application_status", type_="check")
        batch.alter_column(
            "status",
            existing_type=sa.Enum(
                "submitted", "reviewing", "shortlisted", "interview", "interview_completed",
                "offer_made", "hired", "rejected", "withdrawn",
                name="job_application_status", native_enum=False,
            ),
            type_=sa.Enum(
                *application_statuses,
                name="job_application_status", native_enum=False,
                create_constraint=True,
            ),
            existing_nullable=False,
        )

    op.create_table(
        "application_status_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by", sa.String(length=20), nullable=False),
        sa.Column("backfilled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_status_events_application_changed",
        "application_status_events",
        ["application_id", "changed_at"],
        unique=False,
    )

    connection = op.get_bind()
    applications = connection.execute(
        sa.text(
            "SELECT id, status, created_at, updated_at FROM job_applications"
        )
    )
    now = datetime.now(timezone.utc)
    for application in applications:
        changed_at = application.updated_at or application.created_at or now
        connection.execute(
            sa.text(
                """
                INSERT INTO application_status_events
                (id, application_id, from_status, to_status, changed_at, changed_by, backfilled)
                VALUES (:id, :application_id, NULL, :status, :changed_at, 'system', TRUE)
                """
            ),
            {
                "id": str(uuid4()),
                "application_id": application.id,
                "status": getattr(application.status, "value", application.status),
                "changed_at": changed_at,
            },
        )

    connection.execute(
        sa.text(
            """
            UPDATE course_enrollments
            SET completed_at = updated_at
            WHERE status = 'completed' AND completed_at IS NULL
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE candidate_profiles
            SET profile_completed_at = updated_at
            WHERE profile_completed_at IS NULL
              AND full_name IS NOT NULL AND TRIM(full_name) <> ''
              AND governorate_code IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("job_applications", recreate="never") as batch:
        batch.drop_constraint("job_application_status", type_="check")
        batch.alter_column(
            "status",
            existing_type=sa.Enum(
                "submitted", "reviewing", "shortlisted", "interview", "interview_completed",
                "offer_made", "interviewed", "offered", "hired", "rejected", "withdrawn",
                name="job_application_status", native_enum=False,
            ),
            type_=sa.Enum(
                "submitted", "reviewing", "shortlisted", "interview", "interview_completed",
                "offer_made", "hired", "rejected", "withdrawn",
                name="job_application_status", native_enum=False,
                create_constraint=True,
            ),
            existing_nullable=False,
        )
    op.drop_index(
        "ix_application_status_events_application_changed",
        table_name="application_status_events",
    )
    op.drop_table("application_status_events")
    op.drop_column("course_enrollments", "completed_at")
    op.drop_column("candidate_profiles", "last_active_at")
    op.drop_column("candidate_profiles", "profile_completed_at")
    op.drop_column("candidate_profiles", "birth_year")
