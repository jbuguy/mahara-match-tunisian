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
| `DATABASE_URL` | backend | Supabase → **Connect** → **Session pooler** (port 5432). Change the prefix to `postgresql+psycopg://` |
| `SUPABASE_URL` | backend | Supabase → Project Settings → API (`https://<ref>.supabase.co`) |
| `CORS_ORIGINS` | backend | `http://localhost:5173` (comma-separated if several) |
| `APP_ENV` | backend | `development` |
| `VITE_SUPABASE_URL` | frontend | same value as `SUPABASE_URL` |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | frontend | Supabase → Project Settings → API keys (`sb_publishable_...`) |
| `VITE_API_BASE_URL` | frontend | `http://localhost:8006` |

Only `VITE_*` names reach the browser, so `DATABASE_URL` never does.

## 2. Database (once)

Open your Supabase project → **SQL Editor** → **New query**. Paste all of [db/schema.sql](db/schema.sql) and click **Run**.
It creates the tables (row level security on, no policies) and inserts the 24 governorates. Running it again is safe.

## 3. Backend

Python 3.14 is what's installed on the dev machine. The code needs 3.12 or newer.

```bash
cd backend
py -m venv .venv                          # Windows (macOS/Linux: python3 -m venv .venv)
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8006
.venv/Scripts/python -m pytest            # tests, no database needed
```

Check it: <http://localhost:8006/api/v1/health> should return `{"status":"ok","governorates":24}`.

## 4. Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```

The Accueil page shows an **API : ok / erreur** badge, which comes from the health endpoint above.
