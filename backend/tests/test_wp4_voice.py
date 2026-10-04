from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import app as platform_app
from app.security import get_current_employer
from app.wp4_voice import create_wp4_voice_router
from mahara_wp6.services.assistant import get_groq_client

WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 32


class FakeWhisper:
    def __init__(self, text="Transcribed employer answer"):
        self.audio = SimpleNamespace(
            transcriptions=SimpleNamespace(
                create=lambda **_kwargs: SimpleNamespace(text=text),
            ),
        )


def test_employer_voice_transcript_uses_the_authenticated_endpoint():
    app = FastAPI()
    fake_client = FakeWhisper()
    called = []

    def current_employer():
        return object()

    def get_client():
        return fake_client

    def transcribe(client, data, kind):
        called.append((client, data, kind))
        return "Développeuse web"

    app.include_router(create_wp4_voice_router(current_employer, get_client, lambda data: "webm" if data.startswith(WEBM[:4]) else None, transcribe))
    response = TestClient(app).post("/employer-agent/transcribe", files={"file": ("voice.webm", WEBM, "audio/webm")})

    assert response.status_code == 200
    assert response.json() == {"text": "Développeuse web"}
    assert called == [(fake_client, WEBM, "webm")]


def test_employer_voice_requires_auth_and_rejects_invalid_or_large_audio():
    app = FastAPI()
    transcribe_calls = []

    def current_employer():
        raise HTTPException(status_code=401, detail="missing employer login")

    app.include_router(create_wp4_voice_router(
        current_employer,
        FakeWhisper,
        lambda data: None,
        lambda *_args: transcribe_calls.append(True) or "unexpected",
    ))
    client = TestClient(app)

    unauthenticated = client.post("/employer-agent/transcribe", files={"file": ("voice.webm", WEBM, "audio/webm")})
    assert unauthenticated.status_code == 401

    def signed_in():
        return object()

    app.dependency_overrides[current_employer] = signed_in
    invalid = client.post("/employer-agent/transcribe", files={"file": ("voice.webm", b"not audio", "audio/webm")})
    oversized = client.post("/employer-agent/transcribe", files={"file": ("voice.webm", b"\x1a\x45\xdf\xa3" + b"x" * (2 * 1024 * 1024), "audio/webm")})

    assert invalid.status_code == 415
    assert oversized.status_code == 413
    assert transcribe_calls == []


def test_root_api_mounts_employer_voice_route_with_employer_auth():
    fake_client = FakeWhisper()
    platform_app.dependency_overrides[get_current_employer] = lambda: object()
    platform_app.dependency_overrides[get_groq_client] = lambda: fake_client
    try:
        response = TestClient(platform_app).post(
            "/employer-agent/transcribe",
            files={"file": ("voice.webm", WEBM, "audio/webm")},
        )
    finally:
        platform_app.dependency_overrides.pop(get_current_employer, None)
        platform_app.dependency_overrides.pop(get_groq_client, None)

    assert response.status_code == 200
    assert response.json() == {"text": "Transcribed employer answer"}