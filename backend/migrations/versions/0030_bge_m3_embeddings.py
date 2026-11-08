"""Upgrade the knowledge vector column to BGE-M3 embeddings."""

from alembic import op


revision = "0030_bge_m3_embeddings"
down_revision = "0029_national_indicators"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("UPDATE knowledge_chunks SET embedding = NULL, embedding_model = NULL, embedding_dimensions = NULL")
    op.execute(
        "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1024) "
        "USING embedding::vector(1024)"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("UPDATE knowledge_chunks SET embedding = NULL, embedding_model = NULL, embedding_dimensions = NULL")
    op.execute(
        "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(384) "
        "USING embedding::vector(384)"
    )
