from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.schemas import Me
from app.services.users import has_profile

router = APIRouter(tags=["me"])


@router.get("/me", response_model=Me)
def me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Me:
    user = current.user
    return Me(id=user.id, email=user.email, name=current.name, has_profile=has_profile(db, user.id))
