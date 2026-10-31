import asyncio
import importlib
import logging
from pathlib import Path
from typing import Any

from .base import BaseSpeechProvider, SpeechProviderError

logger = logging.getLogger(__name__)


class WhisperProvider(BaseSpeechProvider):
    name = "whisper"

    def __init__(self, settings: Any):
        self.model_id = settings.whisper_model
        self.device = settings.whisper_device
        self.compute_type = settings.whisper_compute_type
        self.beam_size = settings.whisper_beam_size
        self.vad_filter = settings.whisper_vad_filter
        self.language_detection = settings.whisper_language_detection
        self._model = None

    @property
    def capabilities(self) -> dict:
        return {
            "languages": ["ar-TN", "fr"],
            "code_switching": True,
            "timestamps": True,
            "local_inference": True,
            "engine": "faster-whisper",
        }

    def _load_model(self):
        if self._model is None:
            try:
                module = importlib.import_module("faster_whisper")
                device = self.device
                if device == "auto":
                    device = "cuda" if self._cuda_available() else "cpu"
                self._model = module.WhisperModel(self.model_id, device=device, compute_type=self.compute_type)
            except Exception as error:
                raise SpeechProviderError(f"Could not load Whisper model '{self.model_id}'.") from error
        return self._model

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return bool(torch.cuda.is_available())
        except ImportError:
            return False

    def _transcribe_sync(self, audio_file: str | Path, language: str | None) -> dict:
        model = self._load_model()
        requested_language = None if self.language_detection and not language else (language.split("-")[0] if language else None)
        try:
            segments, info = model.transcribe(
                str(audio_file),
                language=requested_language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                word_timestamps=True,
            )
            segment_list = list(segments)
            text = " ".join(segment.text.strip() for segment in segment_list).strip()
            duration = getattr(info, "duration", None)
            detected = getattr(info, "language", None)
            timestamps = [
                {"start": segment.start, "end": segment.end, "text": segment.text.strip()}
                for segment in segment_list
            ]
            return self._result(
                text=text,
                language=language or (f"{detected}-TN" if detected == "ar" else detected),
                duration=duration,
                timestamps=timestamps,
            )
        except SpeechProviderError:
            raise
        except Exception as error:
            raise SpeechProviderError("Whisper transcription failed.") from error

    async def transcribe(self, audio_file: str | Path, language: str | None = None) -> dict:
        return await asyncio.to_thread(self._transcribe_sync, audio_file, language)
