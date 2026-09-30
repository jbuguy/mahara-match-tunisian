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

## 2b. Google login (once)

1. Google Cloud Console → APIs & Services → Credentials → create an **OAuth client ID** of type **Web application**.
   - Authorized JavaScript origin: `http://localhost:5173`
   - Authorized redirect URI: the **Callback URL** shown in Supabase's Google provider panel (`https://<ref>.supabase.co/auth/v1/callback`)
2. Supabase → Authentication → Sign In / Providers → **Google**: enable it, paste the Client ID and Client Secret
   (clear the field first; nothing before or after `GOCSPX-…`), and save.
3. Supabase → Authentication → URL Configuration: **Site URL** `http://localhost:5173`, and add
   `http://localhost:5173/auth/callback` to **Redirect URLs**.

If sign-in fails, `/auth/callback` shows a grey "Détail : …" line. "Unable to exchange external code" means Google
rejected the Client ID/Secret saved in Supabase.

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

## 4. Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```

Every page except `/login` and `/auth/callback` needs a Google sign-in. The Accueil page shows an
**API : ok / erreur** badge, which comes from the health endpoint above.
