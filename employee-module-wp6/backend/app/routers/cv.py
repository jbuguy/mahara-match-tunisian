from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..auth import get_token_claims
from ..db import get_db
from ..schemas import CvImportOut
from ..services.cv_import import MAX_CV_BYTES, UNREADABLE, UnreadableCv, build_draft, file_kind, load_skills, read_text

router = APIRouter(prefix="/me/cv", tags=["cv"])


@router.post("", response_model=CvImportOut)
def import_cv(
    file: UploadFile = File(...),
    _claims: dict[str, Any] = Depends(get_token_claims),  # a valid login is enough: nothing is saved
    db: Session = Depends(get_db),
) -> CvImportOut:
    """Reads a PDF or DOCX CV and returns a draft for the profile form. Nothing is saved, the file isn't kept."""
    data = file.file.read(MAX_CV_BYTES + 1)
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="CV too large (5 MB max)")
    kind = file_kind(file.filename or "", data)
    if kind is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="CV must be a PDF or DOCX")
    try:
        text = read_text(kind, data)
    except UnreadableCv:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=UNREADABLE) from None
    return build_draft(text, load_skills(db))
