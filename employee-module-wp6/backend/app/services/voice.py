"""Voice input for the profile assistant: the candidate's recording → text, with Groq Whisper.

The audio is only held in memory for the request; it's never stored. The text goes back to the chat's text box,
where the candidate can fix it before sending it.
"""

import logging
import re

import groq
from fastapi import status

from .assistant import BUSY, SORRY, AssistantUnavailable

logger = logging.getLogger(__name__)

TRANSCRIBE_MODEL = "whisper-large-v3-turbo"
MAX_AUDIO_BYTES = 2 * 1024 * 1024  # a minute of speech from MediaRecorder is ~0.2-1 MB

CONTENT_TYPES = {"webm": "audio/webm", "ogg": "audio/ogg", "mp4": "audio/mp4", "wav": "audio/wav"}


def audio_kind(data: bytes) -> str | None:
    """'webm', 'ogg', 'mp4' or 'wav' from the file's first bytes (the browser's content type is only a hint).

    MediaRecorder gives webm in Chrome and Edge, ogg in Firefox and mp4 in Safari.
    """
    if data.startswith(b"\x1a\x45\xdf\xa3"):  # EBML header (Matroska / WebM)
        return "webm"
    if data.startswith(b"OggS"):
        return "ogg"
    if data[4:8] == b"ftyp":  # ISO media file (MP4, M4A)
        return "mp4"
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "wav"
    return None


def transcribe(client: groq.Groq, data: bytes, kind: str) -> str:
    """The words spoken in the recording ('' when nothing was understood).

    No language is forced: Whisper detects it, so French, Derja and Arabic all work.
    """
    try:
        result = client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=(f"voix.{kind}", data, CONTENT_TYPES[kind]),
            response_format="json",
            temperature=0,
        )
    except groq.RateLimitError as exc:
        logger.warning("groq rate limit (transcription): %s", exc.message)
        raise AssistantUnavailable(status.HTTP_429_TOO_MANY_REQUESTS, BUSY) from exc
    except groq.APIError as exc:  # connection, timeout, bad key, audio Groq can't read, server errors
        logger.warning("groq transcription error %s: %s", type(exc).__name__, exc.message)
        raise AssistantUnavailable(status.HTTP_502_BAD_GATEWAY, SORRY) from exc
    text = (result.text or "").strip()
    return text if re.search(r"\w", text) else ""  # noise or silence can come back as "." or "..."
