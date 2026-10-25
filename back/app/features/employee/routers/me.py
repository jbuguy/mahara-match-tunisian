from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import CurrentUser, get_current_user
from ..db import get_db
from ..schemas import Me
from ..services.profile import get_profile
from ..services.users import has_profile

router = APIRouter(tags=["me"])


@router.get("/me", response_model=Me)
def me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Me:
    user = current.user
    profile = get_profile(db, user.id)
    return Me(
        id=user.id,
        email=user.email,
        name=current.name or (profile.full_name if profile else None),
        has_profile=has_profile(db, user.id),
    )
