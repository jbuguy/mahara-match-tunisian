"""Add optional professional profiles and service listings."""

from alembic import op
import sqlalchemy as sa


revision = "0017_professional_profiles_services"
down_revision = "0016_employer_notification_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "professional_profiles",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("headline", sa.String(200), nullable=False),
        sa.Column("introduction", sa.String(5000), nullable=False),
        sa.Column("photo_url", sa.String(1000), nullable=True),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column(
            "visibility",
            sa.Enum("private", "public", name="professional_profile_visibility", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("accepting_requests", sa.Boolean(), nullable=False),
        sa.Column("availability", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "ix_professional_profiles_visibility_location",
        "professional_profiles",
        ["visibility", "location"],
    )
    op.create_table(
        "service_listings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("owner_user_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("service_mode", sa.String(30), nullable=False),
        sa.Column("price_type", sa.String(30), nullable=False),
        sa.Column("price_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_max", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "paused", "archived", name="service_listing_status", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "service_mode IN ('remote', 'provider_location', 'customer_location', 'flexible')",
            name="ck_service_listings_mode",
        ),
        sa.CheckConstraint(
            "price_type IN ('fixed', 'hourly', 'starting_at', 'quote', 'negotiable')",
            name="ck_service_listings_price_type",
        ),
        sa.CheckConstraint("price_min IS NULL OR price_min >= 0", name="ck_service_listings_price_min_nonnegative"),
        sa.CheckConstraint("price_max IS NULL OR price_max >= 0", name="ck_service_listings_price_max_nonnegative"),
        sa.CheckConstraint("price_min IS NULL OR price_max IS NULL OR price_max >= price_min", name="ck_service_listings_price_range"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["professional_profiles.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_listings_status_created", "service_listings", ["status", "created_at"])
    op.create_index("ix_service_listings_owner_created", "service_listings", ["owner_user_id", "created_at"])
    op.create_index("ix_service_listings_category_status", "service_listings", ["category", "status"])


def downgrade() -> None:
    op.drop_index("ix_service_listings_category_status", table_name="service_listings")
    op.drop_index("ix_service_listings_owner_created", table_name="service_listings")
    op.drop_index("ix_service_listings_status_created", table_name="service_listings")
    op.drop_table("service_listings")
    op.drop_index("ix_professional_profiles_visibility_location", table_name="professional_profiles")
    op.drop_table("professional_profiles")
