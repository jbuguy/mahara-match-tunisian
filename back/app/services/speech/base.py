from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class SpeechProviderError(RuntimeError):
    """An expected provider or model failure safe to expose as an application error."""


class BaseSpeechProvider(ABC):
    name: str

    @abstractmethod
    async def transcribe(self, audio_file: str | Path | Any, language: str | None = None) -> dict:
        """Return the normalized transcription shape used by every provider."""

    @property
    @abstractmethod
    def capabilities(self) -> dict:
        raise NotImplementedError

    def _result(self, *, text: str, language: str | None, duration: float | None, **extra: Any) -> dict:
        return {
            "text": text.strip(),
            "language": language or "ar-TN",
            "provider": self.name,
            "duration": duration,
            "success": bool(text.strip()),
            "error": None if text.strip() else "No speech recognized",
            **extra,
        }
