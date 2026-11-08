"""Refresh parsed national indicators from approved knowledge documents."""

import argparse
import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.knowledge_base import KnowledgeDocument
from app.national_context import refresh_national_indicators


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    with SessionLocal() as session:
        documents = session.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.external_id.in_((
                    "worldbank-tn-unemployment",
                    "worldbank-tn-youth-unemployment",
                    "worldbank-tn-employment-to-population",
                    "tunisia-agridata-jobs-created",
                )),
                KnowledgeDocument.status == "ready",
            )
        ).all()
        print(f"Refreshed {refresh_national_indicators(session, documents)} observations.")


if __name__ == "__main__":
    main()
