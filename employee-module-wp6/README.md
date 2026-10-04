# Mahara WP6: Employee Module

This package contains the candidate-side WP6 implementation used by the root platform API and frontend. The root platform shares one Supabase PostgreSQL database across WP1, WP2, WP3, WP4, and WP6.
Project rules and history are in [CLAUDE.md](CLAUDE.md) and [docs/sessions/](docs/sessions/).

## 1. Settings

Optional standalone WP6 settings live in `employee-module-wp6/.env`, which is git-ignored. The integrated platform's
`DATABASE_URL`, auth credentials, and shared runtime settings belong in `backend/.env` at the repository root.

```bash
cp .env.example .env   # then fill in the values
```

| Name | Used by | Where to find it |
|---|---|---|
| `GOOGLE_CLIENT_ID` | root backend | Google Cloud Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | root backend | Google Cloud Console → APIs & Services → Credentials |
| `JWT_SECRET` | root backend | Generate a random secret of at least 32 bytes; keep it backend-only |
| `GROQ_API_KEY` | root backend | [console.groq.com](https://console.groq.com) → API Keys; never give it a `VITE_` prefix |
| `GROQ_MODEL` | root backend | `openai/gpt-oss-120b` (the default when left empty) |
| `DATABASE_URL` | root backend only | Supabase PostgreSQL URL in `backend/.env`; direct/session pooler with SSL |

Only `VITE_*` names reach the browser, so `DATABASE_URL` and `GROQ_API_KEY` never do. Without `GROQ_API_KEY` the
app still works; only the profile assistant says it isn't available.

## 2. Shared database

WP1 migrations in the repository root define the shared schema. Configure `backend/.env` and apply them from the root backend:

```powershell
cd backend
python -m app.migrate
```

Use a direct or session-pooler URL with SSL for migrations. Do not apply [db/schema.sql](db/schema.sql); it is retained only as historical WP6 development material and is not a second schema source.

## 2b. Google login (once)

1. In Google Cloud Console, create an OAuth client ID of type **Web application**.
2. Add `http://localhost:8006/api/v1/auth/google/callback` as an authorized redirect URI.
3. Put the client ID and secret in `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `employee-module-wp6/.env`.
4. Set `JWT_SECRET` to a random value of at least 32 bytes. For example, generate one locally with
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

The backend exchanges Google's one-time authorization code, verifies the signed identity token, and issues a
30-minute Mahara access token. If sign-in fails, `/auth/callback` shows the returned error code.

## 3. Integrated runtime

Run the shared API and frontend from the repository root. WP6 routes and services are registered by the root FastAPI app;
do not start a second WP6 database or apply `db/schema.sql`.

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
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
