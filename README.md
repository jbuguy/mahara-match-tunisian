# Mahara Match

Mahara Match is one React frontend and one FastAPI backend for candidate onboarding, job matching, employer hiring, and ministry governance. The frontend is in `front/`; backend feature modules, shared contracts, and providers are in `back/`.

## Features

- Candidate sign-in, profile editing, voice onboarding, CV import, assistant, job matches, roadmaps, and applications.
- Match-specific RAG assistant that answers questions from published offers, validated skills, and active training courses.
- Employer offer drafting, voice input, publishing, and applicant review.
- Ministry skills and occupation governance, market data ingestion, analytics, and monitoring.
- Shared PostgreSQL models/contracts, authentication, database sessions, error handling, LLM clients, and voice helpers.

## Local setup

Requirements: Python 3.11+, Node.js 18+, and PostgreSQL. Configure `back/.env` from `back/.env.example`; set `DATABASE_URL` and a strong `JWT_SECRET`. Optional Google OAuth, Groq, and OpenAI-compatible LLM settings are documented in that file.

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

For voice transcription, install FFmpeg and ensure `ffmpeg` is on `PATH`. The faster-whisper model is downloaded on first use. LLM features require the configured provider; the app can start without external provider credentials.
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
