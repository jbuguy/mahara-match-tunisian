# Session 1: Foundation

Date: 2026-09-30 · Branch: `feature/wp6-employee-module`

Goal: an empty but working app that every later session only adds to. No login or profile code yet.

## What was built

**Database: `db/schema.sql`**
- The 10 tables from CLAUDE.md's Data model:
  - uuid ids with `gen_random_uuid()`
  - check constraints for every allowed value, including `users.role` and `skills.status`
  - foreign keys from the candidate tables with `on delete cascade`
  - row level security on every table, with no policies
- Inserts the 24 governorates (French and Arabic names) with `on conflict do update`.
- Safe to run twice. The `role` and `status` checks are dropped and re-added at the end of the table section, so databases created by an earlier version of the file get them too.
- It was applied to my Supabase project and checked: 10 tables, 24 governorates, both new checks present, and a second run succeeded without errors.

**Backend: `backend/`, FastAPI on port 8006**
- `app/config.py` reads `employee-module-wp6/.env` with pydantic-settings, using the path computed from the code. `extra="ignore"` is set because the frontend's `VITE_*` names live in the same file.
- `app/db.py` creates the engine and session lazily, so the app and the tests start without `DATABASE_URL`. `get_db` is the per-request dependency.
- `app/models.py` holds the SQLAlchemy 2 typed models matching `schema.sql`, plus tuples of the allowed values (`ONBOARDING_PATHS`, `EDUCATION_LEVELS`, `USER_ROLES` and so on).
- `app/routers/health.py` serves `GET /api/v1/health`, which returns `{"status":"ok","governorates":<count>}`, or a 503 error if the database can't be reached.
- `app/main.py` sets up the app, CORS from `CORS_ORIGINS`, and the router under `/api/v1`.
- `tests/test_health.py` has 2 tests (count and database down). They use `TestClient` and a fake session through `dependency_overrides`, so no database is needed.

**Frontend: `frontend/`, Vite on port 5173**
- Stack: Vite 8, React 19, TypeScript 6, Tailwind 4.3 (`@tailwindcss/vite`), shadcn 4 (radix base, "nova" preset), lucide-react 1.49, React Router 8.4 (imports from `react-router`).
- `vite.config.ts` sets `envDir: '..'`, the `@` → `src` alias and port 5173.
- `src/index.css`:
  - the Mahara palette as Tailwind colors (`teal`, `gold`, `gold-foreground`, `page`, `surface`, `ink`, `ink-secondary`, `line`, `danger`), with shadcn's tokens mapped onto it
  - fonts `font-sans` (Work Sans) and `font-heading` (Outfit), loaded from Google Fonts in `index.html`
  - radius 10px
- `src/components/ui/`: `button`, `sheet` and `badge` from shadcn, restyled.
  - `button` sizes are raised to 44px or more (`default` h-11, `lg` h-12, `icon` size-11), and there is a new `gold` variant for the one main action per screen.
  - `sheet`'s close button has French labels.
- `src/components/layout/AppShell.tsx`:
  - below 1024px: a 56px top bar (logo and a hamburger labelled "Ouvrir le menu") and a 300px teal drawer from the left, which closes on navigation
  - from 1024px: a fixed 240px teal sidebar (active item has a light fill and a 3px gold right border) and a 72px top bar with the page name
- Pages:
  - `/login` is standalone, outside the shell
  - `/` Accueil shows the "API : ok / erreur" badge from `/health`
  - `/offres`, `/candidatures` and `/formation` show "Bientôt disponible"
  - `/profil` is a placeholder

**Other:** `README.md` covers setup and running. `.env.example` has placeholders for every variable.

## Env var names used

All of them live in the single git-ignored `employee-module-wp6/.env`:
- Backend: `DATABASE_URL`, `SUPABASE_URL`, `CORS_ORIGINS` (default `http://localhost:5173`), `APP_ENV` (default `development`).
- Frontend: `VITE_API_BASE_URL` (falls back to `http://localhost:8006`), `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`.
- Only `DATABASE_URL` is set right now. The others are unused or have defaults until Session 2.

## Decisions

- **Primary keys:**
  - `candidate_experiences` and `candidate_educations` get an `id` (no natural key exists)
  - `candidate_skills` and `candidate_desired_occupations` use composite keys
  - `candidate_pii` is keyed by `candidate_id`
  - `candidates.user_id` is unique (one profile per user)
- **Column types:** `level` and `priority` are smallint, `confidence` is real, `years_experience` and `duration_months` are `>= 0`.
- **Python:** 3.14 in the venv, because it's the only version installed. The code needs 3.12 or newer.
- **Tests:** `httpx2` is added as a test-only dependency, because the installed Starlette's `TestClient` needs it.
- **Class helpers:** shadcn installed the `cn` package. It was replaced with `clsx` and `tailwind-merge` to match the approved list, and `src/lib/utils.ts` has the classic `cn()`.
- **Geist:** the font package shadcn installed was removed. The design uses Outfit and Work Sans.
- **Health errors:** `/health` returns 503 on database errors, so the frontend badge shows "erreur".

## Known issues

- The database password was pasted in chat once, so it should be rotated. In `DATABASE_URL`, `%` must stay written as `%25`.
- On Windows, stopping `npm run dev` from a tool can leave `node.exe` running on port 5173 (`strictPort` then fails). Kill it with `taskkill //PID <pid> //T //F`.
- If packages are installed while Vite is running, the page goes blank with "Outdated Optimize Dep" errors. Restart with `npx vite --force`.
- Fonts need internet access (Google Fonts). This is accepted in CLAUDE.md.

## What Session 2 should do first

1. Read CLAUDE.md and this file.
2. Ask me to add `SUPABASE_URL`, `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` to `.env`, and to enable the Google provider in Supabase (Authentication → Providers, with the redirect URL `http://localhost:5173`).
3. Install `@supabase/supabase-js` (check its version first), then build `app/auth.py` (ES256 through `PyJWKClient`, lower-cased email, create the `users` row on first login) and the real `/login` page.
