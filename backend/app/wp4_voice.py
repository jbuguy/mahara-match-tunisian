from typing import Any, Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

MAX_AUDIO_BYTES = 2 * 1024 * 1024


def create_wp4_voice_router(
    get_current_employer: Callable[..., Any],
    get_groq_client: Callable[..., Any],
    audio_kind: Callable[[bytes], str | None],
    transcribe: Callable[[Any, bytes, str], str],
) -> APIRouter:
    router = APIRouter(prefix="/employer-agent", tags=["employer-agent"])

    @router.post("/transcribe")
    def transcribe_employer_audio(
        file: UploadFile = File(...),
        _employer: Any = Depends(get_current_employer),
        client: Any = Depends(get_groq_client),
    ) -> dict[str, str]:
        data = file.file.read(MAX_AUDIO_BYTES + 1)
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="recording too large (2 MB max)")
        kind = audio_kind(data)
        if kind is None:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="audio must be webm, ogg, mp4 or wav")
        try:
            return {"text": transcribe(client, data, kind)}
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            message = getattr(error, "message", None)
            if status_code is None or not isinstance(message, str):
                raise
            raise HTTPException(status_code=status_code, detail=message) from error

    return router