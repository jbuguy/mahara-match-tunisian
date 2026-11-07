"""Add professional portfolio links and service areas."""

from alembic import op
import sqlalchemy as sa


revision = "0018_professional_portfolios_service_area"
down_revision = "0017_professional_profiles_services"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("professional_profiles", sa.Column("service_area", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("professional_profiles", sa.Column("portfolio_items", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("service_listings", sa.Column("portfolio_items", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("service_listings", "portfolio_items")
    op.drop_column("professional_profiles", "portfolio_items")
    op.drop_column("professional_profiles", "service_area")
