"""Add opaque public identifiers for professional profiles."""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0035_professional_public_ids"
down_revision = "0034_curated_skill_relationships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "professional_profiles",
        sa.Column("public_id", sa.String(length=36), nullable=True),
    )
    connection = op.get_bind()
    profile_ids = connection.execute(
        sa.text("SELECT user_id FROM professional_profiles")
    ).scalars().all()
    for _user_id in profile_ids:
        connection.execute(
            sa.text(
                "UPDATE professional_profiles SET public_id = :public_id "
                "WHERE user_id = :user_id"
            ),
            {"public_id": str(uuid4()), "user_id": _user_id},
        )
    with op.batch_alter_table("professional_profiles") as batch_op:
        batch_op.alter_column(
            "public_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
    op.create_index(
        "uq_professional_profiles_public_id",
        "professional_profiles",
        ["public_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_professional_profiles_public_id",
        table_name="professional_profiles",
    )
    op.drop_column("professional_profiles", "public_id")
