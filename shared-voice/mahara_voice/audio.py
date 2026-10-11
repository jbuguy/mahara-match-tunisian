"""Audio format detection and bounded reads for browser voice uploads."""

from typing import BinaryIO

AUDIO_CONTENT_TYPES = {
    "webm": "audio/webm",
    "ogg": "audio/ogg",
    "mp4": "audio/mp4",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "aac": "audio/aac",
}


def audio_kind(data: bytes) -> str | None:
    """Return a supported audio extension based on bytes, not the client MIME hint."""
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"
    if data.startswith(b"OggS"):
        return "ogg"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "mp4"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "wav"
    if data.startswith(b"ID3") or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "mp3"
    if len(data) > 1 and data[0] == 0xFF and data[1] & 0xF6 == 0xF0:
        return "aac"
    return None


def read_limited(stream: BinaryIO, max_bytes: int) -> bytes:
    """Read at most max_bytes plus one byte, allowing callers to detect oversize uploads."""
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    return stream.read(max_bytes + 1)
