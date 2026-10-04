# mahara match — AI-Powered Job Matching Platform (Tunisia)

An AI-powered platform tackling youth unemployment in Tunisia by addressing four distinct sub-problems: degree/skills mismatch, hiring discrimination, women exiting the labor force, and the gap between job-seeker expectations and market reality — for **both skilled/graduate and unskilled/informal workers**.

> Status: Academic project (final deliverable = deployed platform, not just a prototype).

---

## Problem statement

Unemployment in Tunisia isn't one problem — it's four:

| # | Sub-problem | Target group |
|---|---|---|
| A | Degree/skills mismatch — graduate unemployment rising (24.2%, up from 22.5%) despite falling overall unemployment | Graduates |
| B | Hiring discrimination — 14.2% unemployment for male graduates vs 32% for equally qualified women | Graduates, esp. women |
| C | Women exiting the labor force — ~29% female labor participation vs ~64% male; 71%+ of working-age women outside the labor market entirely | Women |
| D | Expectations vs. market reality — search friction, sector avoidance, ~2/3 of youth prefer entrepreneurship over existing jobs | Skilled & unskilled |

**Design principle**: we explicitly serve both skilled/graduate workers *and* unskilled/informal workers, who are easier to overlook (no CV, no formal history, possible literacy constraints). Every feature is checked against: *"does this work for someone with no formal CV?"*

---

## Platform architecture

Mahara Match is structured as a single production platform with clear service boundaries, not a collection of disconnected demo apps. The canonical data layer is PostgreSQL, shared contracts are owned by WP1, and each module exposes a well-defined API contract while the platform shell remains a coherent operational surface.

| Layer | Responsibility |
|---|---|
| Core platform | API shell, auth, deployment, observability, health checks, environment config |
| WP1 | Canonical data model, Postgres schema, contracts, migrations, validation |
| WP2 | Candidate onboarding and conversational intake |
| WP3 | Matching, skill scoring, candidate-to-offer ranking |
| WP4 | Employer workflows and AI-assisted job publishing |
| WP6 | Employee journey, candidate profile, applications, roadmap |

This keeps the repository production-like: one runtime model, one database, module boundaries, and shared contracts instead of isolated package copies.

---

## AI Features

| Feature | Sub-problems addressed | WP |
|---|---|---|
| Employer-side agent (conversational job-post generation) | B, D | WP4 |
| Case-worker agent (multi-week plan for informal workers) | C, D | WP6/WP2 |
| Bias check on job posts | B | WP4 |
| Skill-to-job matcher | A, D | WP3 |
| Interview + negotiation prep agent | A, D | WP6 |
| Path-builder for informal workers | C, D | WP6/WP2 |
| Sector reality simulator | D | WP6 |
| Fraud/scam post detection | — | WP4 (stretch) |

Feature list is a working hypothesis — to be validated with real users (both skilled and unskilled) before finalizing.

---

## Tech stack

- **Backend**: FastAPI (Python)
- **Frontend**: React / Next.js
- **Database**: PostgreSQL (+ pgvector where needed)
- **Vector search**: pgvector in PostgreSQL; no separate vector database is needed for the current schema
- **LLM serving**: vLLM / TGI / Ollama — one shared model endpoint, consumed by all WPs (avoid duplicating model hosting per WP)
- **Models**: Open-weight, Arabic/Derja-capable (e.g. Jais, AceGPT, or Qwen2.5/Llama 3.1 as multilingual fallback)
- **Auth**: JWT
- **Containerization**: Docker / Docker Compose
- **CI/CD**: GitHub Actions
- **Deployment target**: [cloud provider TBD — AWS/GCP/Azure/university cloud]

---

## Data strategy

Hybrid approach:
1. **MVP phase**: open datasets (e.g. O*NET, BLS) to validate core flows (matching, sector preview, skill mapping) with low legal risk.
2. **In parallel**: build a Tunisia-compliant pipeline — prioritize partnerships/licensed APIs over scraping, add Tunisia-specific sector taxonomy, cover French/Arabic/Tunisian dialect, validate against a small curated sample of real Tunisian job posts.

No PII stored unless strictly necessary and consented; anonymized/aggregated analytics preferred.

---

## Getting started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (frontend)
- Access to the shared LLM endpoint (see `/docs/llm-access.md`)

### Local setup
Start PostgreSQL and apply the WP1 and WP6 schema initialization scripts:

```powershell
docker compose up -d db
```

Compose initializes the WP6 tables automatically for a new database volume. For an existing Postgres volume, apply `employee-module-wp6/db/schema.sql` once using `psql` before starting the backend.

Configure the root API from `backend/.env.example` (copy it to `backend/.env`). Set Google OAuth credentials and register this exact authorized redirect URI in Google Cloud:

```text
http://localhost:8000/auth/google/callback
```

Then run the API and frontend in separate terminals:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

WP2 voice intake uses `faster-whisper` and `pydub`. Install FFmpeg and make sure
`ffmpeg` is available on `PATH` so browser recordings can be decoded. The small
Whisper model is downloaded the first time a voice response is transcribed.
Fresh databases apply the onboarding-session migration through Docker Compose;
for an existing database, run `python -m app.migrate` from `backend`.

### Production validation
The repo keeps package-specific tooling isolated, but the platform still behaves like a coherent production system with a single canonical database and a shared API shell. Use the root backend for service-level validation, then run package-specific suites when changing module-local code.

```bash
# root-level platform checks
cd backend && pytest

# package-specific suites
cd ../data-layer-wp1 && pytest
cd ../employee-module-wp6/backend && pytest
cd ../skill-matching-wp3 && pytest
```

### Running a single WP service (e.g. WP4)
```bash
cd services/wp4-employer-module
uvicorn app.main:app --reload
```
---

## Repo structure (proposed)

```
/services
  /wp1-data-layer
  /wp2-onboarding-agent
  /wp3-skill-matching
  /wp4-employer-module
  /wp6-employee-module
/docs
  llm-access.md
  data-strategy.md
  deployment.md
/infra
  docker-compose.yml
.github/workflows/
```

---

## Contributing

- One feature branch per user story (e.g. `wp4/employer-account-creation`)
- PRs require at least one review
- Don't modify another WP's shared schema/tables without flagging it in the relevant Slack channel first
- Keep each WP's README up to date with its own endpoints/setup

---

## License

[TBD]