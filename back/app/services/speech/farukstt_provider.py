import asyncio
import importlib
import logging
from pathlib import Path
from typing import Any

from .base import BaseSpeechProvider, SpeechProviderError

logger = logging.getLogger(__name__)


class FarukSTTProvider(BaseSpeechProvider):
    name = "farukstt"

    def __init__(self, settings: Any):
        self.model_id = settings.farukstt_model
        self.device = settings.farukstt_device
        self.compute_type = settings.farukstt_compute_type
        self.language = settings.farukstt_language
        self._processor = None
        self._model = None
        self._torch = None

    @property
    def capabilities(self) -> dict:
        return {
            "languages": ["ar-TN", "fr"],
            "code_switching": "documented by model card; verify for production data",
            "timestamps": False,
            "local_inference": True,
            "engine": "transformers",
            "license": "not declared by model repository; commercial use requires rights review",
        }

    def _load_model(self):
        if self._model is not None:
            return self._processor, self._model, self._torch
        try:
            transformers = importlib.import_module("transformers")
            torch = importlib.import_module("torch")
            dtype = getattr(torch, self.compute_type, torch.float32)
            device = self.device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            self._processor = transformers.AutoProcessor.from_pretrained(self.model_id)
            self._model = transformers.AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_id, torch_dtype=dtype, low_cpu_mem_usage=True
            ).to(device)
            self._model.eval()
            self._device = device
            self._torch = torch
            return self._processor, self._model, torch
        except Exception as error:
            raise SpeechProviderError(
                f"Could not load FarukSTT model '{self.model_id}'. Install transformers/torch and check available memory."
            ) from error

    def _transcribe_sync(self, audio_file: str | Path, language: str | None) -> dict:
        processor, model, torch = self._load_model()
        try:
            import librosa
            audio, sample_rate = librosa.load(str(audio_file), sr=16000, mono=True)
            inputs = processor(audio, sampling_rate=sample_rate, return_tensors="pt")
            inputs = {key: value.to(self._device) for key, value in inputs.items()}
            forced = None
            selected_language = language or (None if self.language == "auto" else self.language)
            decoder_language = selected_language.split("-")[0] if selected_language else None
            if decoder_language:
                forced = processor.get_decoder_prompt_ids(language=decoder_language, task="transcribe")
            with torch.inference_mode():
                output = model.generate(**inputs, forced_decoder_ids=forced)
            text = processor.batch_decode(output, skip_special_tokens=True)[0].strip()
            duration = len(audio) / sample_rate
            return self._result(text=text, language=selected_language or "ar-TN", duration=duration)
        except SpeechProviderError:
            raise
        except Exception as error:
            raise SpeechProviderError("FarukSTT transcription failed.") from error

    async def transcribe(self, audio_file: str | Path, language: str | None = None) -> dict:
        return await asyncio.to_thread(self._transcribe_sync, audio_file, language)
