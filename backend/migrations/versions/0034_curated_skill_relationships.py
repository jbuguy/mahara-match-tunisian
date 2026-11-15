"""Add curated skill relationships for candidate matching."""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0034_curated_skill_relationships"
down_revision = "0033_candidate_roadmap_proposals"
branch_labels = None
depends_on = None


SEED_RELATIONSHIPS = (
    ("Python", "Data Analysis", "RELATED_TO", 0.55, 0.8),
    ("Excel", "Data Analysis", "RELATED_TO", 0.45, 0.75),
    ("Power BI", "Data Analysis", "RELATED_TO", 0.5, 0.8),
    ("SQL", "Data Analysis", "FOUNDATION_OF", 0.35, 0.8),
)


def upgrade() -> None:
    op.create_table(
        "skill_relationships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("from_skill_id", sa.String(length=36), nullable=False),
        sa.Column("to_skill_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=20), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "relation_type IN ('RELATED_TO', 'FOUNDATION_OF')",
            name="ck_skill_relationships_relation_type",
        ),
        sa.CheckConstraint(
            "strength >= 0 AND strength <= 1",
            name="ck_skill_relationships_strength",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_skill_relationships_confidence",
        ),
        sa.CheckConstraint(
            "from_skill_id != to_skill_id",
            name="ck_skill_relationships_distinct_skills",
        ),
        sa.ForeignKeyConstraint(
            ["from_skill_id"], ["skills_catalogue.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["to_skill_id"], ["skills_catalogue.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_skill_id",
            "to_skill_id",
            "relation_type",
            name="uq_skill_relationships_edge",
        ),
    )
    op.create_index(
        "ix_skill_relationships_from_type",
        "skill_relationships",
        ["from_skill_id", "relation_type"],
    )
    op.create_index(
        "ix_skill_relationships_to_type",
        "skill_relationships",
        ["to_skill_id", "relation_type"],
    )

    connection = op.get_bind()
    skill_ids = dict(
        connection.execute(
            sa.text(
                "SELECT canonical_name_fr, id FROM skills_catalogue "
                "WHERE canonical_name_fr IN ('Python', 'Excel', 'Power BI', "
                "'SQL', 'Data Analysis')"
            )
        ).all()
    )
    for from_name, to_name, relation_type, strength, confidence in SEED_RELATIONSHIPS:
        from_skill_id = skill_ids.get(from_name)
        to_skill_id = skill_ids.get(to_name)
        if from_skill_id is None or to_skill_id is None:
            continue
        connection.execute(
            sa.text(
                "INSERT INTO skill_relationships "
                "(id, from_skill_id, to_skill_id, relation_type, strength, confidence, source) "
                "VALUES (:id, :from_id, :to_id, :relation_type, :strength, :confidence, :source)"
            ),
            {
                "id": str(uuid4()),
                "from_id": from_skill_id,
                "to_id": to_skill_id,
                "relation_type": relation_type,
                "strength": strength,
                "confidence": confidence,
                "source": "initial_curated_taxonomy",
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_skill_relationships_to_type",
        table_name="skill_relationships",
    )
    op.drop_index(
        "ix_skill_relationships_from_type",
        table_name="skill_relationships",
    )
    op.drop_table("skill_relationships")
