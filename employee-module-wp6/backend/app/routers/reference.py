from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_token_claims
from app.db import get_db
from app.schemas import GovernorateOut, OccupationOut, SkillOut
from app.services import reference

router = APIRouter(prefix="/reference", tags=["reference"], dependencies=[Depends(get_token_claims)])


@router.get("/governorates", response_model=list[GovernorateOut])
def governorates(db: Session = Depends(get_db)):
    return reference.list_governorates(db)


@router.get("/skills", response_model=list[SkillOut])
def skills(q: str = Query("", max_length=100), db: Session = Depends(get_db)):
    return reference.search_skills(db, q)


@router.get("/occupations", response_model=list[OccupationOut])
def occupations(q: str = Query("", max_length=100), db: Session = Depends(get_db)):
    return reference.search_occupations(db, q)
