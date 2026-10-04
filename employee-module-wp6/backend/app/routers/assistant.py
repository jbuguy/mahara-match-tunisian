from typing import Any

import groq
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_token_claims
from app.config import Settings, get_settings
from app.db import get_db
from app.schemas import AssistantChatIn, AssistantChatOut, TranscriptOut
from app.services.assistant import SORRY, AssistantUnavailable, assistant_turn, get_groq_client, load_occupations
from app.services.cv_import import load_skills
from app.services.voice import MAX_AUDIO_BYTES, audio_kind, transcribe

router = APIRouter(prefix="/me/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatOut)
def chat(
    body: AssistantChatIn,
    _claims: dict[str, Any] = Depends(get_token_claims),  # a valid login is enough: nothing is saved
    client: groq.Groq = Depends(get_groq_client),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> AssistantChatOut:
    """One turn of the profile assistant: its reply and the form fields to fill. Nothing is saved or stored."""
    try:
        # The skills and occupations lists are only read when the answer names some.
        return assistant_turn(client, settings.groq_model, body, lambda: load_skills(db), lambda: load_occupations(db))
    except AssistantUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=SORRY) from None


@router.post("/transcribe", response_model=TranscriptOut)
def transcribe_audio(
    file: UploadFile = File(...),
    _claims: dict[str, Any] = Depends(get_token_claims),
    client: groq.Groq = Depends(get_groq_client),
) -> TranscriptOut:
    """A voice answer (webm, ogg, mp4 or wav, 2 MB max) as text. The audio is only held in memory, never stored."""
    data = file.file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="recording too large (2 MB max)")
    kind = audio_kind(data)
    if kind is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="audio must be webm, ogg, mp4 or wav",
        )
    try:
        return TranscriptOut(text=transcribe(client, data, kind))
    except AssistantUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
