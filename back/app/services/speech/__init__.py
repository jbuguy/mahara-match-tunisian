"""Pluggable local speech-to-text providers."""

from .base import BaseSpeechProvider, SpeechProviderError
from .speech_factory import create_speech_provider
from .speech_service import SpeechService

__all__ = ["BaseSpeechProvider", "SpeechProviderError", "SpeechService", "create_speech_provider"]
