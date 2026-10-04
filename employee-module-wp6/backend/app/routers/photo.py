from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.services.photo import JPEG_START, MAX_PHOTO_BYTES, get_photo, set_photo

router = APIRouter(prefix="/me/photo", tags=["photo"])

NO_PROFILE = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")


@router.get("", response_class=Response, responses={200: {"content": {"image/jpeg": {}}}})
def read_photo(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    photo = get_photo(db, current.user.id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no photo")
    return Response(content=photo, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


@router.put("", status_code=status.HTTP_204_NO_CONTENT)
def upload_photo(
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """A JPEG the browser has already cropped and shrunk to 256x256."""
    photo = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(photo) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="photo too large")
    if not photo.startswith(JPEG_START):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="photo must be a JPEG")
    if not set_photo(db, current.user.id, photo):
        raise NO_PROFILE


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    """Back to the Google photo."""
    if not set_photo(db, current.user.id, None):
        raise NO_PROFILE
