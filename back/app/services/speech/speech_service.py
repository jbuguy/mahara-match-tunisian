import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from .base import SpeechProviderError
from .speech_factory import create_speech_provider


class SpeechService:
    def __init__(self, settings: Any):
        self.settings = settings
        self.provider = create_speech_provider(settings)

    @property
    def capabilities(self) -> dict:
        return self.provider.capabilities

    async def transcribe_bytes(self, data: bytes, suffix: str, language: str | None = None) -> dict:
        with tempfile.NamedTemporaryFile(prefix="mahara-stt-", suffix=suffix, delete=False) as handle:
            handle.write(data)
            path = Path(handle.name)
        try:
            return await self.provider.transcribe(path, language)
        finally:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


@lru_cache
def get_speech_service():
    from ...config import get_settings
    return SpeechService(get_settings())
