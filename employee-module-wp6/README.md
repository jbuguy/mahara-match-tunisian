# Mahara WP6: Employee Module

This module is the candidate side of Mahara Match. It has a FastAPI backend on port 8006 and a Vite + React frontend on port 5173.
Project rules and history are in [CLAUDE.md](CLAUDE.md) and [docs/sessions/](docs/sessions/).

## 1. Settings: one `.env` file

All settings live in `employee-module-wp6/.env`, which is git-ignored. The backend and the frontend both read it.

```bash
cp .env.example .env   # then fill in the values
```

| Name | Used by | Where to find it |
|---|---|---|
| `DATABASE_URL` | backend | Local PostgreSQL from root `compose.yaml`: `postgresql+psycopg://mahara:mahara@localhost:5432/mahara_match` |
| `GOOGLE_CLIENT_ID` | backend | Google Cloud Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | backend | Google Cloud Console → APIs & Services → Credentials |
| `JWT_SECRET` | backend | Generate a random secret of at least 32 bytes; keep it backend-only |
| `API_BASE_URL` | backend | `http://localhost:8006` |
| `FRONTEND_URL` | backend | `http://localhost:5173` |
| `CORS_ORIGINS` | backend | `http://localhost:5173` (comma-separated if several) |
| `APP_ENV` | backend | `development` |
| `GROQ_API_KEY` | backend | [console.groq.com](https://console.groq.com) → API Keys (free plan, `gsk_...`). Never give it a `VITE_` prefix |
| `GROQ_MODEL` | backend | `openai/gpt-oss-120b` (the default when left empty) |
| `VITE_API_BASE_URL` | frontend | `http://localhost:8006` |

Only `VITE_*` names reach the browser, so `DATABASE_URL` and `GROQ_API_KEY` never do. Without `GROQ_API_KEY` the
app still works; only the profile assistant says it isn't available.

## 2. Database (once)

From the repository root, start PostgreSQL and apply the shared migrations:

```powershell
docker compose up -d db
```

The first database initialization applies the ordered files in root `migrations/`. Apply [db/schema.sql](db/schema.sql)
to the same database for the WP6 compatibility additions, including `candidate_pii.photo`; it is safe to re-run:

```powershell
docker compose exec db psql -U mahara -d mahara_match -f /wp6/schema.sql
```

## 2b. Google login (once)

1. In Google Cloud Console, create an OAuth client ID of type **Web application**.
2. Add `http://localhost:8006/api/v1/auth/google/callback` as an authorized redirect URI.
3. Put the client ID and secret in `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `employee-module-wp6/.env`.
4. Set `JWT_SECRET` to a random value of at least 32 bytes. For example, generate one locally with
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

The backend exchanges Google's one-time authorization code, verifies the signed identity token, and issues a
30-minute Mahara access token. If sign-in fails, `/auth/callback` shows the returned error code.

## 3. Backend

Python 3.14 is what's installed on the dev machine. The code needs 3.12 or newer.

```bash
cd backend
py -m venv .venv                          # Windows (macOS/Linux: python3 -m venv .venv)
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m scripts.seed_dev  # dev skills (SK-9001...) and occupations (OC-9001...), once
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8006
.venv/Scripts/python -m pytest -rs        # tests
```

The seed script only runs when `APP_ENV` is `dev` or `development`. Running it again is safe.

The profile and reference tests use the database from `DATABASE_URL`. Each test runs inside a transaction that is rolled back,
so nothing is kept. They are skipped when the database can't be reached (`-rs` shows why).

Check it: <http://localhost:8006/api/v1/health> should return `{"status":"ok","governorates":24}`.

On start, the backend opens a few PostgreSQL connections in the background so the first requests aren't the slowest.
On Windows, if a change doesn't seem to take effect,
`--reload` may be stuck: touch `app/main.py` or restart the backend.

## 4. Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```

Every page except `/login` and `/auth/callback` needs a Google sign-in. The Accueil page shows an
**API : ok / erreur** badge, which comes from the health endpoint above.
