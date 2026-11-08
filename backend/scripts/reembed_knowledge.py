"""Re-embed all knowledge chunks with the currently configured embedding model."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.knowledge_base import (
    EMBEDDING_BATCH_SIZE,
    KnowledgeChunk,
    KnowledgeDocument,
    generate_embeddings,
)


async def reembed_knowledge() -> int:
    with SessionLocal() as session:
        chunks = list(
            session.scalars(
                select(KnowledgeChunk).order_by(KnowledgeChunk.created_at, KnowledgeChunk.id)
            )
        )
        for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch = chunks[start : start + EMBEDDING_BATCH_SIZE]
            embeddings, model = await generate_embeddings([chunk.content for chunk in batch])
            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding
                chunk.embedding_model = model
                chunk.embedding_dimensions = len(embedding)
            session.commit()

        document_ids = {chunk.document_id for chunk in chunks}
        documents = session.scalars(
            select(KnowledgeDocument).where(KnowledgeDocument.id.in_(document_ids))
        )
        for document in documents:
            document.status = "ready"
            document.ingestion_error = None
        session.commit()

    return len(chunks)


def main() -> None:
    count = asyncio.run(reembed_knowledge())
    print(f"Re-embedded {count} knowledge chunks.")


if __name__ == "__main__":
    main()
