# Session 7: Assistant voice input

Date: 2026-09-30 · Branch: `feature/wp6-employee-module`

Goal: the candidate can speak to Assistant Mahara instead of typing. For safety, the transcript always goes into the
text box first, so the candidate can fix it before pressing "Envoyer". There's no text-to-speech and no automatic
sending, and neither audio nor conversations are stored.

## What was built

**Backend: `app/services/voice.py`** (groq 1.7.0)
- `audio_kind(data)` recognises the recording from its **first bytes**; the browser's content type is only a hint:
  - WebM (EBML header `1A 45 DF A3`): Chrome, Edge
  - Ogg (`OggS`): Firefox
  - MP4 (`ftyp` at byte 4): Safari
  - WAV (`RIFF….WAVE`)
- `transcribe(client, data, kind)` calls `client.audio.transcriptions.create` with:
  - `model="whisper-large-v3-turbo"`
  - `file=("voix.<kind>", data, "audio/<kind>")`
  - `response_format="json"`, `temperature=0`
  - **no `language`**, so Whisper detects it and French, Derja and Arabic all work
- The text is trimmed. A result with no letters or digits becomes `""`: a live test with a tone returned `"."`.
- Errors reuse Session 6's `AssistantUnavailable` and French messages:
  - rate limit → 429 "Un instant, réessayez dans quelques secondes."
  - any other Groq error → 502 "Désolé, l'assistant n'a pas pu répondre…"
- It uses the same `GROQ_API_KEY` and the same client (`get_groq_client`, 503 without a key). No new env var.

**Backend: `POST /api/v1/me/assistant/transcribe`** (in `app/routers/assistant.py`)
- Multipart field `file`. It only checks the token (`get_token_claims`) and doesn't touch the database.
- The audio is read into memory (2 MB + 1 byte at most) and never written anywhere.
- Answers:
  - `{text}` (`TranscriptOut` in `app/schemas.py`)
  - 413 over 2 MB (`MAX_AUDIO_BYTES`)
  - 415 if it isn't webm/ogg/mp4/wav
  - 503 without a key, 429 on a rate limit, 502 on other errors, 401 without login

**Frontend**
- `src/lib/api.ts`: `transcribeAudio(blob)` (named `voix.webm|ogg|mp4|wav` after its type) and `MAX_AUDIO_BYTES`.
- `src/components/assistant/use-voice-recorder.ts`, `useVoiceRecorder(onText)`:
  - **states:** `idle` → `starting` (microphone permission) → `recording` (seconds) → `transcribing`
  - **MediaRecorder** takes the first format the browser supports among `audio/webm;codecs=opus`, `audio/webm`,
    `audio/ogg;codecs=opus`, `audio/ogg` and `audio/mp4`
  - **stops automatically at 60 s** (`MAX_RECORDING_SECONDS`)
  - **`cancel()`** ("Annuler") throws the recording away without sending it
  - **after stopping**, the microphone tracks are stopped, which turns off the browser's recording light
  - **closing the chat while recording** throws the recording away
  - **a recording under 0.8 s** isn't sent (a tap by mistake; Whisper would invent words from silence)
  - **French messages:**
    - microphone refused: "Autorisez le micro dans votre navigateur, puis réessayez. Vous pouvez aussi écrire votre
      réponse."
    - no microphone: "Aucun micro trouvé…"
    - browser can't record: "Votre navigateur ne permet pas d'enregistrer la voix. Écrivez votre réponse."
    - too short, too long, or nothing heard ("Nous n'avons rien entendu…")
    - the backend's message for 429/502/503
    - no connection
- `src/components/assistant/AssistantChat.tsx`:
  - **"Parler"** (lucide `Mic`, 44 px, `aria-label="Parler"`, with the visible word too) sits next to "Envoyer".
  - **While recording** it is a red button with a pulsing white dot and the time (`0:12`); clicking it stops.
    Beside it are "Parlez… (1 min max)" and a small "Annuler". "Envoyer" is hidden until the transcript is back.
  - **While transcribing:** a spinner and "Transcription…".
  - **The transcript is added** after what's already typed. On large screens the text box then gets focus with the
    cursor at the end, so Enter sends. On phones it doesn't get focus, so the keyboard doesn't pop up.
  - **The text box is now full width and grows** to about 4 lines (`field-sizing: content`); the buttons moved to a row
    below it. With the one-line box in the narrow side panel, a spoken sentence showed only its last words, so it
    couldn't be checked. Enter sends and Shift+Enter adds a line.
  - **Message limit:** raised from 500 to 1,000 characters (the backend's limit per message), so a minute of speech
    fits.
  - **Errors:** shown in red above the text box. They go away when the candidate types or sends.

**Tests:** 144 in total (20 new in `tests/test_voice.py`). Whisper is replaced by a fake client, so no network or key
is needed.
- Success: the model name, no `language`, and the file's name, bytes and type as sent to Groq. Each of the 4 formats is
  recognised from its bytes, even with a wrong content type.
- Empty, `"."` and `"..."` become `""`; Arabic text is kept.
- Too big → 413 with Groq not called; wrong type (text, PDF, empty file) → 415 with Groq not called.
- 429 → the French message; other errors (400, 500, connection) → 502; missing key → 503; no login → 401.

**Checked in a headless browser** with a fake microphone and scripted API answers, at 1440 px and 390 px. Covered:
- recording, the counter and stopping
- the automatic stop at 60 s (a real 60-second wait)
- the transcript added to typed text and not sent until Enter
- "Annuler" (no transcription call)
- a too-short tap, a 429, a refused microphone and a browser without MediaRecorder
- no horizontal scroll, and 44 px buttons

A real Whisper call was also made with a generated WAV to confirm the parameters are accepted (0.7 s).

## Model and recording limit

- Speech-to-text: **`whisper-large-v3-turbo`** on Groq's free plan, with no forced language.
- Recording: **60 seconds at most** (automatic stop), and the upload must be **2 MB at most**. By estimate, not
  measurement, a minute of Opus/WebM is a few hundred KB and Safari's MP4/AAC about 1 MB, so both fit.

## Env var names added

None. Voice uses the same `GROQ_API_KEY` (backend only).

## Decisions

- **Format from the bytes, not the content type:** browsers send different types (`audio/webm;codecs=opus`,
  `audio/mp4`…), and a renamed file must not reach Groq. This is the same rule as the CV import.
- **Transcript into the text box only:** the candidate always sees and can fix what was understood. That matters for
  Derja, which Whisper writes in different ways.
- **Appended, not replaced:** a candidate can type part of an answer and say the rest.
- **Focus after a transcript on large screens only:** on phones, focusing would open the keyboard over the chat.
- **Minimum 0.8 s:** a quick tap would send near-silence, and Whisper invents words from silence.
- **Visible "Parler" label** on the mic button, as well as the requested `aria-label`, following the design rule of a
  text label on every icon.
- **Red while recording** uses the danger colour (`#C62828`). The design keeps it for errors, but the session prompt
  asked for a red recording button.

## Known issues

- **Real-voice check:** I marked the session done without reporting the French and Derja voice results in detail.
  Transcription quality on real speech (especially Derja) is still to be confirmed.
- **Derja spelling:** Whisper has no Derja setting, so it may write Derja in Arabic letters or in a French-like
  spelling. This wasn't measured here. The candidate can fix the text in the box before sending.
- **Hallucinations on silence or noise:** Whisper is known to sometimes return phrases nobody said. The transcript is
  never sent automatically, so the candidate can delete it.
- **Free-plan limits:** Whisper has its own limits (requests and audio seconds per hour and per day; see
  console.groq.com → Settings → Limits). Past them the candidate sees "Un instant…".
- **Microphone access** needs a secure page: it works on `http://localhost`. Other devices on the network would need
  HTTPS.
- **Firefox and `field-sizing`:** Firefox doesn't support `field-sizing: content` yet. There the text box stays one line
  high with a scroll bar. Chrome, Edge and Safari grow it.
- **Not tried on a real phone:** only a 390 px browser window with a fake microphone was tested.
- **Dev servers:** uvicorn `--reload` on Windows often misses changes. Restart the backend after backend edits.

## What the next session should do first

1. Read CLAUDE.md and all files in `docs/sessions/`.
2. Session 8 (later) is the switch to the team Supabase project. Nothing in the assistant or voice code depends on it,
   apart from the skills and occupations lists read for name matching.
