from sqlalchemy.orm import Session

from mahara_data.repositories.taxonomy import (
    list_governorates as shared_list_governorates,
    search_occupations as shared_search_occupations,
    search_skills as shared_search_skills,
)

SEARCH_LIMIT = 20

def list_governorates(db: Session):
    return shared_list_governorates(db)


def search_skills(db: Session, q: str):
    return shared_search_skills(db, q, limit=SEARCH_LIMIT)


def search_occupations(db: Session, q: str):
    return shared_search_occupations(db, q, limit=SEARCH_LIMIT)
