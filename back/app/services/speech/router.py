import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from .base import SpeechProviderError
from .speech_service import SpeechService, get_speech_service

MAX_AUDIO_BYTES = 25 * 1024 * 1024
MIME_SUFFIXES = {
    "audio/webm": ".webm", "audio/ogg": ".ogg", "audio/wav": ".wav",
    "audio/x-wav": ".wav", "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/aac": ".aac",
}


def create_speech_router() -> APIRouter:
    router = APIRouter(prefix="/api/speech", tags=["speech"])

    @router.get("/provider")
    def provider(service: SpeechService = Depends(get_speech_service)):
        return {"provider": service.provider.name, "capabilities": service.capabilities}

    @router.post("/transcribe")
    async def transcribe(
        audio: Annotated[UploadFile, File(...)],
        language: Annotated[str | None, Form()] = None,
        service: SpeechService = Depends(get_speech_service),
    ):
        data = await audio.read(MAX_AUDIO_BYTES + 1)
        if not data:
            raise HTTPException(status_code=400, detail={"code": "audio_empty", "message": "Audio is empty."})
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Audio exceeds 25 MB.")
        suffix = MIME_SUFFIXES.get(audio.content_type or "") or Path(audio.filename or "").suffix.lower()
        if suffix not in MIME_SUFFIXES.values():
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported audio format.")
        try:
            result = await service.transcribe_bytes(data, suffix, language)
        except SpeechProviderError as error:
            raise HTTPException(status_code=503, detail={"code": "stt_unavailable", "message": str(error)}) from error
        except Exception as error:
            raise HTTPException(status_code=500, detail={"code": "transcription_failed", "message": "Transcription failed."}) from error
        if not result["success"]:
            raise HTTPException(status_code=422, detail={"code": "transcription_empty", "message": result["error"]})
        return result

    return router
