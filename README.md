# Mahara Match

Mahara Match is a French-first employment and training platform for Tunisia.
It connects candidates, employers, training providers, ministry administrators,
and platform operators around skills, job opportunities, career preparation,
training, and labour-market data.

The application uses a React frontend and a FastAPI/PostgreSQL backend.

## Platform capabilities

- Candidate profiles, CV-assisted profile extraction, skills, job matches,
  applications, career roadmaps, and interview preparation.
- Career assistants in Derja, Arabic, and French, with saved conversation
  sessions and optional voice transcription and speech synthesis.
- Technical and behavioural assessments with deterministic and AI-assisted
  feedback. Assessment text answers are not executed.
- Employer offers, applicant management, workforce planning, and hiring outcomes.
- Training-provider course catalogues, candidate enrollments, and completion
  tracking.
- Ministry dashboards with privacy-preserving aggregate analytics.
- Role-based access, JWT authentication, organisation ownership checks,
  audit events, and Tunisian labour-market data collections.

## Technology

| Layer | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite |
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL with pgvector |
| Tests | Vitest and pytest |
| Optional AI services | OpenAI-compatible LLM, embeddings, Whisper, and text-to-speech |

## Prerequisites

- Node.js 22.12+ (Node.js 24 is also supported)
- Python 3.11+
- Docker Desktop, or a local PostgreSQL installation with pgvector support
- PowerShell 7 is recommended for the Windows commands below

## Quick start

The following commands start PostgreSQL and run the database migrations,
frontend, and API locally.

1. Create the local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start PostgreSQL:

   ```powershell
   docker compose up postgres -d
   ```

3. Create a virtual environment and install the backend dependencies:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r backend/requirements.txt
   ```

4. Apply database migrations:

   ```powershell
   python -m alembic -c backend/alembic.ini upgrade head
   ```

5. Install frontend dependencies:

   ```powershell
   npm install
   ```

6. Start the API in one terminal:

   ```powershell
   $env:PYTHONPATH = "backend"
   python -m uvicorn app.main:app --reload
   ```

   The backend serves `http://127.0.0.1:8000`. Useful health endpoints are:

   - `GET http://127.0.0.1:8000/health/live`
   - `GET http://127.0.0.1:8000/health/ready`

7. Start the frontend in another terminal:

   ```powershell
   npm run dev
   ```

   The frontend is available at `http://localhost:5173`.

## Configuration

Copy `.env.example` to `.env` and update the values for your machine. Do not
commit `.env` or real credentials. In particular:

- Replace `JWT_SECRET_KEY` with a random value of at least 32 characters.
- Use the SQLAlchemy PostgreSQL connection format:
  `postgresql+psycopg://<user>:<password>@<host>:5432/mahara_match`.
- Keep demo users disabled outside local development.
- Set frontend origins explicitly when changing ports or hosts.
- Set `VITE_API_BASE_URL` when the API is not available at
  `http://127.0.0.1:8000`.

Generate a JWT secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The Docker Compose database uses:

```text
Database: mahara_match
User: postgres
Password: password
Port: 5432
```

Change the Compose credentials before using the stack beyond a local machine.

## Demo accounts

Demo users are for local development only. Enable them by setting
`MAHARA_ENABLE_DEMO_USERS=true` and choosing a local-only password in
`MAHARA_DEMO_PASSWORD`, then seed them:

```powershell
$env:PYTHONPATH = "backend"
python -m app.seed_demo_users
```

| Role | Demo email |
| --- | --- |
| Candidate | `candidate@demo.maharamatch.test` |
| Employer | `employer@demo.maharamatch.test` |
| Ministry admin | `ministry@demo.maharamatch.test` |
| Training provider | `provider@demo.maharamatch.test` |
| Operator | `operator@demo.maharamatch.test` |

All demo accounts use `MAHARA_DEMO_PASSWORD`. The seed command is repeatable and
does not reset passwords for existing accounts.

To create a realistic local dataset with stable candidates, employers, offers,
applications, and courses:

```powershell
$env:PYTHONPATH = "backend"
python -m scripts.seed_demo_data
```

The demo dataset also creates 20 clearly labelled synthetic offers and six
synthetic, ministry observatory indicators for the
`ministry@demo.maharamatch.test` account. Synthetic records are marked in their
titles or metadata and must not be presented as real market data.

To reset development records without dropping the database schema or migration
history:

```powershell
$env:PYTHONPATH = "backend"
python -m scripts.reset_demo_database --confirm
```

Never use demo seeding or reset scripts against production.

## Optional local AI and voice services

The platform can use an OpenAI-compatible local language model through
LM Studio or another compatible server. Optional embeddings, speech
transcription, and text-to-speech services are available through Docker Compose
profiles.

```powershell
# PostgreSQL and the multilingual embedding service
docker compose --profile rag up -d postgres embeddings

# Whisper and text-to-speech
docker compose --profile voice up -d whisper tts
```

Configure the matching `MAHARA_*_BASE_URL`, model, and API-key variables from
`.env.example`. Core profile and job-search features do not require the optional
services. If an assistant or voice provider is unavailable, the backend should
continue to respond without claiming that an unavailable service succeeded.

The default embedding model is `BAAI/bge-m3` and produces 1024-dimensional
vectors. After changing the pgvector migration, re-embed all existing chunks
with the configured embedding service:

```powershell
$env:PYTHONPATH = "backend"
python -m scripts.reembed_knowledge
```

## Labour-market data

The backend includes a reviewed data pipeline for annual Tunisia and France
labour-market observations. Collected files are written locally under
`backend/data/`, which is ignored by Git. Each run records source metadata,
retrieval time, record counts, and checksums.

To import the reviewed data already available to the local pipeline:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingest_labour_data --data-dir backend/data/open
```

Only ingest sources with verified availability, methodology, and reuse terms.
Tunisia observations and France observations must remain country-specific.
French data provides comparative context only and is not evidence of
Tunisia-specific demand. Statistical trends are context, not individual hiring
predictions.

## API overview

The interactive API documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

Representative endpoints include:

| Area | Endpoints |
| --- | --- |
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Candidate profile | `GET/PATCH /candidate/profile`, `POST /candidate/profile/cv` |
| Career assistant | `/candidate/assistant/sessions`, `/candidate/assistant/chat` |
| Opportunities | `GET /candidate/matches`, `POST /candidate/applications` |
| Interview preparation | `/candidate/interview-prep/...` |
| Employer planning | `/employer/planning-sessions`, `/employer/offers` |
| Courses | `/marketplace/courses`, candidate enrollment routes |

Protected endpoints require a JWT from the sign-in response. Ownership and
organization membership are enforced independently of frontend navigation.

## Roles and privacy

| Role | Principal access |
| --- | --- |
| Candidate | Own profile, roadmaps, assistant sessions, applications, assessments, and course enrollments |
| Employer | Own organization offers, workforce plans, and applicants |
| Ministry admin | Referentials, reviewed imports, exports, and aggregate indicators |
| Training provider | Own courses and associated enrollment records |
| Operator | Service status and audit metadata; no candidate records |

Candidate profile values, assistant messages, audio, and other sensitive data
must not be copied into audit details. Assistant messages remain in candidate
sessions, employer applicant and provider enrollment access is scoped to the
organization, and ministry indicators expose aggregates rather than candidate
records.

## Checks

Run frontend tests and build:

```powershell
npm test
npm run build
```

Run backend tests:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest
```

Validate that migrations can be generated as SQL:

```powershell
python -m alembic -c backend/alembic.ini upgrade head --sql
```

## Project documentation

- [Current tasks](TASKS.md)
- [Audit baseline](docs/AUDIT.md)
- [Pilot release gates](docs/PILOT_RELEASE_GATES.md)
- [Location data sources](docs/location-data-sources.md)
- [Location data review](docs/location-data-review.md)
- [Labour-market data structure](docs/MINISTRY_LABOUR_MARKET_DATA_STRUCTURE.md)
- [Change log](CHANGELOG.md)
