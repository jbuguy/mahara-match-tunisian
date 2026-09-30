from types import SimpleNamespace

import groq
import httpx
import pytest

from app.auth import get_token_claims
from app.config import Settings, get_settings
from app.db import get_db
from app.main import app
from app.services.assistant import BUSY, NO_KEY, SORRY, get_groq_client
from app.services.voice import MAX_AUDIO_BYTES, TRANSCRIBE_MODEL, audio_kind

URL = "/api/v1/me/assistant/transcribe"

# The first bytes of each format MediaRecorder can produce, plus some audio after them.
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 2000
OGG = b"OggS" + b"\x00" * 2000
MP4 = b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 2000
WAV = b"RIFF\x24\x08\x00\x00WAVEfmt " + b"\x00" * 2000


class FakeWhisper:
    """Stands in for groq.Groq's audio.transcriptions: returns `text`, or raises `error`."""

    def __init__(self, text: str = "", error: Exception | None = None):
        self.text, self.error, self.calls = text, error, []
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


def status_error(cls, status_code: int):
    response = httpx.Response(status_code, request=httpx.Request("POST", "https://api.groq.com/openai/v1/audio"))
    return cls("error", response=response, body=None)


@pytest.fixture
def signed_in(client):
    """A valid login; no database (the endpoint doesn't need one)."""
    app.dependency_overrides[get_token_claims] = lambda: {"email": "amine@example.tn"}
    app.dependency_overrides[get_db] = lambda: None


def use(fake: FakeWhisper) -> FakeWhisper:
    app.dependency_overrides[get_groq_client] = lambda: fake
    return fake


def upload(client, data: bytes, name: str = "voix.webm", content_type: str = "audio/webm;codecs=opus"):
    return client.post(URL, files={"file": (name, data, content_type)})


def test_transcribes_a_recording(client, signed_in):
    fake = use(FakeWhisper("  esmi Amine, men Sousse  "))

    response = upload(client, WEBM)

    assert response.status_code == 200
    assert response.json() == {"text": "esmi Amine, men Sousse"}
    (call,) = fake.calls
    assert call["model"] == TRANSCRIBE_MODEL == "whisper-large-v3-turbo"
    assert "language" not in call  # auto-detect: French and Derja both work
    name, data, content_type = call["file"]
    assert (name, data, content_type) == ("voix.webm", WEBM, "audio/webm")


@pytest.mark.parametrize(("data", "kind"), [(WEBM, "webm"), (OGG, "ogg"), (MP4, "mp4"), (WAV, "wav")])
def test_each_recording_format(client, signed_in, data, kind):
    fake = use(FakeWhisper("Je m'appelle Amira"))
    # The type is read from the bytes: Safari's "audio/mp4" or a missing content type change nothing.
    response = upload(client, data, name="blob", content_type="application/octet-stream")
    assert response.status_code == 200
    assert fake.calls[0]["file"][0] == f"voix.{kind}"


@pytest.mark.parametrize("text", ["   ", ".", " ... "])  # a tone gave "." in a live test
def test_nothing_understood_gives_empty_text(client, signed_in, text):
    use(FakeWhisper(text))
    assert upload(client, WEBM).json() == {"text": ""}


def test_arabic_text_is_kept(client, signed_in):
    use(FakeWhisper("إسمي أمين من سوسة"))
    assert upload(client, WEBM).json() == {"text": "إسمي أمين من سوسة"}


def test_too_big(client, signed_in):
    fake = use(FakeWhisper("x"))
    response = upload(client, WEBM[:4] + b"\x00" * MAX_AUDIO_BYTES)
    assert response.status_code == 413
    assert fake.calls == []


@pytest.mark.parametrize("data", [b"not audio at all", b"%PDF-1.7 ...", b""])
def test_wrong_type(client, signed_in, data):
    fake = use(FakeWhisper("x"))
    response = upload(client, data, name="voix.webm", content_type="audio/webm")  # the name and type lie
    assert response.status_code == 415
    assert fake.calls == []


def test_rate_limit(client, signed_in):
    use(FakeWhisper(error=status_error(groq.RateLimitError, 429)))
    response = upload(client, WEBM)
    assert response.status_code == 429
    assert response.json() == {"detail": BUSY}


@pytest.mark.parametrize("error", [
    status_error(groq.BadRequestError, 400),  # e.g. audio Groq can't decode
    status_error(groq.InternalServerError, 500),
    groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com")),
])
def test_other_errors(client, signed_in, error):
    use(FakeWhisper(error=error))
    response = upload(client, WEBM)
    assert response.status_code == 502
    assert response.json() == {"detail": SORRY}


def test_missing_key(client, signed_in):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, groq_api_key=None)
    response = upload(client, WEBM)
    assert response.status_code == 503
    assert response.json() == {"detail": NO_KEY}


def test_requires_login(client, signed_out):
    assert upload(client, WEBM).status_code == 401


def test_audio_kind():
    assert [audio_kind(data) for data in (WEBM, OGG, MP4, WAV, b"RIFF\x00\x00\x00\x00AVI ", b"")] == [
        "webm", "ogg", "mp4", "wav", None, None,
    ]
