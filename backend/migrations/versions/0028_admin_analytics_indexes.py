"""Add indexes supporting cache-friendly admin aggregations."""

from alembic import op


revision = "0028_admin_analytics_indexes"
down_revision = "0027_skills_catalogue_normalisation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_users_role_created_at", "users", ["role", "created_at"])
    op.create_index("ix_candidate_profiles_governorate", "candidate_profiles", ["governorate_code"])
    op.create_index("ix_candidate_profiles_birth_governorate", "candidate_profiles", ["birth_year", "governorate_code"])
    op.create_index("ix_job_offers_governorate_created", "job_offers", ["governorate_code", "created_at"])
    op.create_index("ix_job_applications_created_status", "job_applications", ["created_at", "status"])
    op.create_index("ix_course_enrollments_status_created", "course_enrollments", ["status", "created_at"])
    op.create_index("ix_training_courses_status_published", "training_courses", ["status", "published_at"])
    op.create_index("ix_organisations_sector", "organisations", ["sector"])
    op.create_index("ix_candidate_skills_skill_user", "candidate_skills", ["skill_id", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_candidate_skills_skill_user", table_name="candidate_skills")
    op.drop_index("ix_organisations_sector", table_name="organisations")
    op.drop_index("ix_training_courses_status_published", table_name="training_courses")
    op.drop_index("ix_course_enrollments_status_created", table_name="course_enrollments")
    op.drop_index("ix_job_applications_created_status", table_name="job_applications")
    op.drop_index("ix_job_offers_governorate_created", table_name="job_offers")
    op.drop_index("ix_candidate_profiles_birth_governorate", table_name="candidate_profiles")
    op.drop_index("ix_candidate_profiles_governorate", table_name="candidate_profiles")
    op.drop_index("ix_users_role_created_at", table_name="users")
