from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.services.speech.base import SpeechProviderError
from app.services.speech.farukstt_provider import FarukSTTProvider
from app.services.speech.router import create_speech_router
from app.services.speech.speech_factory import create_speech_provider
from app.services.speech.speech_service import SpeechService
from app.services.speech.whisper_provider import WhisperProvider


def settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_factory_selects_provider_from_configuration():
    assert isinstance(create_speech_provider(settings(stt_provider="whisper")), WhisperProvider)
    assert isinstance(create_speech_provider(settings(stt_provider="farukstt")), FarukSTTProvider)


def test_factory_rejects_unknown_provider():
    with pytest.raises(SpeechProviderError, match="Unsupported STT_PROVIDER"):
        create_speech_provider(settings(stt_provider="unknown"))


def test_whisper_transcription_is_normalized_without_loading_weights(monkeypatch, tmp_path):
    provider = WhisperProvider(settings())
    provider._model = SimpleNamespace(transcribe=lambda *_args, **kwargs: (
        iter([SimpleNamespace(text=" Bonjour ", start=0.0, end=1.2)]),
        SimpleNamespace(language="fr", duration=1.2),
    ))
    result = __import__("asyncio").run(provider.transcribe(tmp_path / "voice.wav"))
    assert result["text"] == "Bonjour"
    assert result["provider"] == "whisper"
    assert result["success"] is True
    assert result["timestamps"][0]["start"] == 0.0


def test_farukstt_transcription_is_normalized_with_mocked_model(monkeypatch, tmp_path):
    provider = FarukSTTProvider(settings())
    class Processor:
        def __call__(self, *_args, **_kwargs): return {"input_features": FakeTensor()}
        def batch_decode(self, *_args, **_kwargs): return ["bonjour tounes"]
        def get_decoder_prompt_ids(self, **_kwargs): return []
    class Model:
        def generate(self, **_kwargs): return object()
    class FakeTensor:
        def to(self, _device): return self
    fake_torch = SimpleNamespace(inference_mode=lambda: __import__("contextlib").nullcontext())
    provider._processor, provider._model, provider._torch, provider._device = Processor(), Model(), fake_torch, "cpu"
    monkeypatch.setitem(__import__("sys").modules, "librosa", SimpleNamespace(load=lambda *_args, **_kwargs: ([0.0] * 16000, 16000)))
    result = __import__("asyncio").run(provider.transcribe(tmp_path / "voice.wav", "fr"))
    assert result["text"] == "bonjour tounes"
    assert result["provider"] == "farukstt"
    assert result["duration"] == 1.0


def test_speech_endpoint_validates_audio_and_returns_provider_metadata(monkeypatch):
    app = FastAPI()
    service = SpeechService(settings())
    async def fake_transcribe(_data, _suffix, language=None):
        return service.provider._result(text="salem", language=language, duration=1.0)
    service.transcribe_bytes = fake_transcribe
    app.include_router(create_speech_router())
    from app.services.speech.speech_service import get_speech_service
    app.dependency_overrides[get_speech_service] = lambda: service
    client = TestClient(app)
    assert client.get("/api/speech/provider").json()["provider"] == "whisper"
    response = client.post("/api/speech/transcribe", files={"audio": ("voice.wav", b"wav", "audio/wav")})
    assert response.status_code == 200
    assert response.json()["text"] == "salem"
    assert client.post("/api/speech/transcribe", files={"audio": ("voice.txt", b"x", "text/plain")}).status_code == 415
