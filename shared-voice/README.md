# Shared voice primitives

`mahara_voice` is the platform-owned audio utility package for work packages that accept spoken input. It provides:

- `audio_kind(data)`: identify supported formats from the bytes rather than trusting a browser MIME header.
- `read_limited(stream, max_bytes)`: read at most `max_bytes + 1` so the caller can reject oversized uploads.
- `transcribe_groq(client, data, kind, model=..., filename_prefix=...)`: call Groq Whisper without imposing work-package-specific error handling.

Consumers own authentication, upload limits, user-facing errors, and domain interpretation. WP6 and WP4 use Groq Whisper; WP2 keeps its local Faster Whisper model and Derja extraction pipeline. Audio remains in memory or request-scoped temporary storage and must not be logged or persisted.

Install the package from the repository root with `python -m pip install -e ./shared-voice`, or use the editable dependency in each integrated backend requirements file.
