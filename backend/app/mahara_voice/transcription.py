"""Provider adapter for Groq Whisper transcription."""

from typing import Any

from .audio import AUDIO_CONTENT_TYPES

DEFAULT_GROQ_TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"


def transcribe_groq(
    client: Any,
    data: bytes,
    kind: str,
    *,
    model: str = DEFAULT_GROQ_TRANSCRIPTION_MODEL,
    filename_prefix: str = "voice",
) -> str:
    """Transcribe an in-memory audio recording; provider-specific error mapping stays with the caller."""
    content_type = AUDIO_CONTENT_TYPES.get(kind)
    if content_type is None:
        raise ValueError(f"Unsupported audio kind: {kind}")
    result = client.audio.transcriptions.create(
        model=model,
        file=(f"{filename_prefix}.{kind}", data, content_type),
        response_format="json",
        temperature=0,
    )
    return (result.text or "").strip()
