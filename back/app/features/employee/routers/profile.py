from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import CurrentUser, get_current_user
from ..db import get_db
from ..schemas import ProfileIn, ProfileOut
from ..services.profile import get_profile, save_profile

router = APIRouter(prefix="/me/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def read_profile(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileOut:
    profile = get_profile(db, current.user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    return profile


@router.put("", response_model=ProfileOut)
def write_profile(
    body: ProfileIn, current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileOut:
    return save_profile(db, current.user, body)
