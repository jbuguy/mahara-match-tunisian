from typing import Any

from .base import SpeechProviderError
from .farukstt_provider import FarukSTTProvider
from .whisper_provider import WhisperProvider


def create_speech_provider(settings: Any):
    provider = settings.stt_provider.lower().strip()
    if provider == "whisper":
        if not settings.whisper_model.strip():
            raise SpeechProviderError("WHISPER_MODEL must be configured when STT_PROVIDER=whisper.")
        return WhisperProvider(settings)
    if provider == "farukstt":
        if not settings.farukstt_model.strip():
            raise SpeechProviderError("FARUKSTT_MODEL must be configured when STT_PROVIDER=farukstt.")
        return FarukSTTProvider(settings)
    raise SpeechProviderError(f"Unsupported STT_PROVIDER '{settings.stt_provider}'. Use 'whisper' or 'farukstt'.")
