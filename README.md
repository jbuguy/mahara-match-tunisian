# Mahara Match

Mahara Match is one React frontend and one FastAPI backend for candidate onboarding, job matching, employer hiring, and ministry governance. The frontend is in `front/`; backend feature modules, shared contracts, and providers are in `back/`.

## Features

- Candidate sign-in, profile editing, voice onboarding, CV import, assistant, job matches, roadmaps, and applications.
- Match-specific RAG assistant that answers questions from published offers, validated skills, and active training courses.
- Employer offer drafting, voice input, publishing, and applicant review.
- Ministry skills and occupation governance, market data ingestion, analytics, and monitoring.
- Shared PostgreSQL models/contracts, authentication, database sessions, error handling, LLM clients, and voice helpers.

## Local setup

Requirements: Python 3.11+, Node.js 18+, and PostgreSQL. Configure `back/.env` from `back/.env.example`; set `DATABASE_URL` and a strong `JWT_SECRET`. Optional Google OAuth, Groq, and OpenAI-compatible LLM settings are documented in that file. Email verification and password reset require SMTP settings (`SMTP_HOST`, `SMTP_FROM_EMAIL`, and, when required, SMTP credentials) before the API can deliver links.

Apply ordered SQL migrations and start the API in one terminal:

```powershell
cd back
python -m pip install -r requirements.txt
python -m app.migrate
python -m uvicorn app.main:app --reload --port 8000
```

Start the frontend in another terminal:

```powershell
cd front
npm install
npm run dev
```

For voice transcription, install FFmpeg and ensure `ffmpeg` is on `PATH`. The STT service is provider-based: both local providers implement the same normalized response and the frontend never loads model weights. Models are lazy-loaded on the first transcription request.

### Local STT providers

The active provider is selected with one setting in `back/.env`:

```dotenv
STT_PROVIDER=whisper
# or: STT_PROVIDER=farukstt
```

The endpoint is `POST /api/speech/transcribe` with an `audio` multipart field and an optional `language` field. `GET /api/speech/provider` exposes the active provider and non-sensitive capabilities.

The default Whisper provider uses `faster-whisper`:

```powershell
cd back
python -m pip install faster-whisper pydub
```

Configure `WHISPER_MODEL` with a compatible CTranslate2 model or local model directory. The verified `TheBiggyBang/whisper-small-tunisian-derja` repository is a Transformers checkpoint (not already CTranslate2), is Apache-2.0 licensed, and reports roughly 32% Tunisian test WER. Convert it before using it with faster-whisper:

```powershell
python -m pip install ctranslate2 transformers
ct2-transformers-converter --model TheBiggyBang/whisper-small-tunisian-derja --output_dir models/whisper-small-tunisian-derja --quantization int8
```

Then set `WHISPER_MODEL=./models/whisper-small-tunisian-derja`. `WHISPER_DEVICE=auto` selects CUDA when available; use `cpu` with `int8`, or `cuda` with `float16`/`int8_float16` as appropriate. `WHISPER_BEAM_SIZE`, `WHISPER_VAD_FILTER`, and `WHISPER_LANGUAGE_DETECTION` control decoding.

FarukSTT is a Transformers checkpoint, not a `faster-whisper`/CTranslate2 checkpoint:

```powershell
cd back
python -m pip install transformers accelerate librosa
# Install a PyTorch build appropriate for the host (CPU or CUDA) from https://pytorch.org/
```

The published Hugging Face repository currently found for this model is `medyas/FarukSTT`; `FARUKxAUTO/FarukSTT` does not resolve. It is based on `openai/whisper-large-v3`, uses `WhisperForConditionalGeneration`, and can be loaded with `AutoProcessor` and `AutoModelForSpeechSeq2Seq`. The model card reports Tunisian Derja, French/English code-switching, and approximately 32% WER on its validation set, so the transcript must remain user-reviewable. The repository does not declare a license. Treat commercial use as blocked until the author grants or documents suitable rights.

FarukSTT is approximately 1.5B parameters in F32 form and requires substantially more memory than a small Whisper model. A GPU with roughly 8–16 GB VRAM is a practical starting point depending on dtype and audio length; CPU inference is supported but slow and memory-intensive. `FARUKSTT_DEVICE=auto` selects CUDA when available, and `FARUKSTT_COMPUTE_TYPE=float16` is recommended only on compatible CUDA hardware; use `float32` on CPU.

The provider-specific environment variables are documented in [`back/.env.example`](back/.env.example). Audio is validated, written only to a request-scoped temporary file, and removed after inference. Model failures return an explicit error; the service never silently falls back to another provider. Candidate onboarding still extracts structured answers only after STT returns; the existing review screen remains the confirmation boundary before profile data is used.
The match assistant also requires an OpenAI-compatible embeddings endpoint configured by `LLM_BASE_URL`. Set `LLM_EMBEDDING_MODEL` to a multilingual model that returns 768 dimensions (the shared pgvector schema uses 768). Public matching knowledge is indexed on first use and refreshed when its source content changes.

## Verification

```powershell
cd back
python -m pytest -q
```

```powershell
cd front
npm run build
```

## Repository layout

```text
back/
  app/
    features/
      employee/       # candidate profile, CV, assistant, shared employee API
      employer/       # employer agent and voice transcription route
      matching/       # ranking, roadmap, and matching API
      onboarding/     # voice intake, transcription, question audio, offer text
      ministry/       # ministry governance and analytics
  mahara_data/        # canonical ORM models and Pydantic contracts
  mahara_voice/       # shared audio utilities
  shared_llm/         # shared OpenAI-compatible client
  contracts/          # published JSON Schema documents
front/
  src/
    lib/              # shared API client and browser helpers
    pages/            # unified routes and feature pages
migrations/           # ordered PostgreSQL migrations
```

Historical work-package design documents are retained under `docs/work-packages/`; they are not imported or launched by the application.
