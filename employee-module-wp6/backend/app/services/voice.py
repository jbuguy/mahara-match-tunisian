"""Voice input for the profile assistant: the candidate's recording → text, with Groq Whisper.

The audio is only held in memory for the request; it's never stored. The text goes back to the chat's text box,
where the candidate can fix it before sending it.
"""

import logging
import re
import groq
from fastapi import status
from mahara_voice import audio_kind as shared_audio_kind
from mahara_voice import transcribe_groq

from .assistant import BUSY, SORRY, AssistantUnavailable

logger = logging.getLogger(__name__)

TRANSCRIBE_MODEL = "whisper-large-v3-turbo"
MAX_AUDIO_BYTES = 2 * 1024 * 1024  # a minute of speech from MediaRecorder is ~0.2-1 MB

def audio_kind(data: bytes) -> str | None:
    """'webm', 'ogg', 'mp4' or 'wav' from the file's first bytes (the browser's content type is only a hint).

    MediaRecorder gives webm in Chrome and Edge, ogg in Firefox and mp4 in Safari.
    """
    return shared_audio_kind(data)


def transcribe(client: groq.Groq, data: bytes, kind: str) -> str:
    """The words spoken in the recording ('' when nothing was understood).

    No language is forced: Whisper detects it, so French, Derja and Arabic all work.
    """
    try:
        text = transcribe_groq(client, data, kind, model=TRANSCRIBE_MODEL, filename_prefix="voix")
    except groq.RateLimitError as exc:
        logger.warning("groq rate limit (transcription): %s", exc.message)
        raise AssistantUnavailable(status.HTTP_429_TOO_MANY_REQUESTS, BUSY) from exc
    except groq.APIError as exc:  # connection, timeout, bad key, audio Groq can't read, server errors
        logger.warning("groq transcription error %s: %s", type(exc).__name__, exc.message)
        raise AssistantUnavailable(status.HTTP_502_BAD_GATEWAY, SORRY) from exc
    return text if re.search(r"\w", text) else ""  # noise or silence can come back as "." or "..."
