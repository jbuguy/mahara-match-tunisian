
# CLAUDE.md: Mahara WP6 Employee Module, project memory

This file lives at `employee-module-wp6/CLAUDE.md` (uppercase name, so Claude Code finds it on any OS). Read it first, every session, before doing anything else. Then read **all** files in
`employee-module-wp6/docs/sessions/` (if the folder exists yet), in order, for the history of what's been built and why.
Scope and sequencing are already decided in this file and in each session prompt: don't re-derive them.

## Project

Mahara Match: Tunisian national employment platform. The team shares one GitHub repo
(`jbuguy/mahara-match-tunisian`); each person works independently on their own branch.
This branch builds the candidate side (WP6, Employee Module). **Current scope is only two things:**

1. **Authentication**: sign in with Google.
2. **Candidate profile**: the candidate creates it by filling a form **or** by importing a CV (PDF/DOCX),
   then can view and edit it.
   Everything else (offers, applications, roadmap) waits until this is done. UI is in French; users may have
   low literacy, so keep copy short, buttons big, and a text label on every icon.

## Constraints

- **Only edit files inside `employee-module-wp6/`.** Never touch other teams' folders or root files.
- **Ignore `data-layer-wp1/` and `supabase/` completely** (another teammate's work on `main`): don't read them,
  import from them, install them, or edit/delete them. This module has its own small schema and models.
- Branch `feature/wp6-employee-module`. Never commit to `main`.
- **Own Supabase project for now**, set up with our own `employee-module-wp6/db/schema.sql`. Its table and column
  names match the team's so a later switch is mostly env vars. Don't add tables or columns beyond the ones listed
  in the Data model below without asking.
- Local only: no deploy config, no Docker, no CI. Free services only.
- Context is cleared between sessions. Every session ends with the app **working locally**. If a session
  runs long, cut scope, not the test-and-document step at the end.

## Stack: don't add libraries beyond this list without asking

- **Backend** (`employee-module-wp6/backend/`, port **8006**): Python 3.12+ (dev machine uses 3.14), FastAPI, SQLAlchemy 2
  (our own models in `app/models.py`), psycopg 3, pydantic-settings, PyJWT[crypto], python-multipart, pypdf,
  python-docx, pytest, and `httpx2` for tests only (Starlette's `TestClient` needs it).
- **Frontend** (`employee-module-wp6/frontend/`, port **5173**): Vite + React + TypeScript, Tailwind CSS v4,
  shadcn/ui, lucide-react, React Router v8, @supabase/supabase-js. Plain `fetch` + `useState`, no extra
  state or form libraries. Packages that shadcn installs itself are approved too (clsx, tailwind-merge,
  class-variance-authority, radix-ui, tw-animate-css).
- **Auth + DB:** Supabase. Google OAuth only: no passwords, no SMS, no signup form.

### Version traps (your training data is older than these)

- React Router **v8**: import from `react-router`. `react-router-dom` no longer exists.
- Tailwind **v4**: `@import "tailwindcss";` + `@theme {}` in CSS, `@tailwindcss/vite` plugin.
- Supabase login tokens are **ES256**. Verify with PyJWT `PyJWKClient` on
  `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, `audience="authenticated"`. Never use the old HS256 JWT secret.
- The frontend uses the **publishable** key (`sb_publishable_...`). The backend needs no Supabase key.
- DB connection: the **session pooler** string (port 5432) as `postgresql+psycopg://...`.
  The direct connection string is IPv6-only and usually fails at home. In the Supabase dashboard it's under
  Connect → Direct → Session pooler. The user must be `postgres.<project-ref>` (plain `postgres` fails with
  "no tenant identifier"), and special characters in the password must be URL-encoded (`%` → `%25`, `@` → `%40`).

## How it works (keep it this simple)

- **Login:** the frontend calls `supabase.auth.signInWithOAuth({ provider: 'google' })`. That's the only thing
  the frontend does with Supabase.
- **Data:** everything else goes through the FastAPI backend with `Authorization: Bearer <access_token>`.
  The backend checks the token, finds the user by email, and reads/writes the tables with the models in `app/models.py`.
  Why not query Supabase from React like GLAM PRO: row level security is on with no policies (same as the team's
  database), so the browser can't read tables directly; a frontend-only version would break when we switch projects.
- Backend layout: `app/main.py` (app + routers), `app/config.py`, `app/db.py`, `app/models.py` (SQLAlchemy tables),
  `app/auth.py`, `app/routers/` (thin), `app/services/` (logic), `app/schemas.py` (request/response models), `tests/`.
  Database setup lives in `employee-module-wp6/db/schema.sql` (run once by hand in the Supabase SQL Editor).
- **CV import** is done inside this backend: read the text with pypdf / python-docx, pull out email, phone,
  skills that match the `skills` table, education and experience lines, and return a **draft** the candidate
  reviews in the form. Nothing is saved and the file isn't stored until they press "Enregistrer".

## Data model (our `db/schema.sql`; names match the team's schema so we can switch later)

`db/schema.sql` is the source of truth for keys and types; this section is the summary.

```text
governorates    code (pk, e.g. TN-11), name_fr, name_ar                  -- 24 rows inserted by schema.sql
users           id, email (unique), role='candidate', preferred_language='fr', last_login_at
candidates      id, user_id (unique: one profile per user), onboarding_path, literacy_level, governorate_code, education_level,
                years_experience, languages (jsonb [{code, level}]), summary, available_from,
                consent_version, consent_given_at
candidate_pii   candidate_id (pk), full_name, email, phone     (identity kept apart from the profile)
candidate_skills        (candidate_id, skill_id) pk, level 1-4, source ('self_declared' | 'cv'), confidence
candidate_experiences   id, candidate_id, job_title_raw, employer_name, start_date, end_date, duration_months, description
candidate_educations    id, candidate_id, level, field_of_study, institution, graduation_year
candidate_desired_occupations  (candidate_id, occupation_id) pk, priority
skills          id, code (unique), label_fr, alt_labels (jsonb), skill_type, status      -- filled by seed_dev.py
occupations     id, code (unique), title_fr                                              -- filled by seed_dev.py
```

- All ids are `uuid default gen_random_uuid()`; every table has row level security turned on with no policies.
- Allowed values (plain text columns with a check constraint, same values as the team uses):
  `onboarding_path` cv_upload | derja_detailed · `literacy_level` literate | basic | non_literate ·
  `skill_type` hard | soft | language · skill `source` self_declared | cv · `users.role` candidate | employer | admin |
  ministry | training_provider · `skills.status` draft | validated | deprecated · `education_level` none | primary |
  lower_secondary | baccalaureate | vocational_cap | vocational_btp | vocational_bts | licence | master | engineer | doctorate.
- Link a Google login to `users` by email: **always lower-case the email in code** before saving or looking it up
  (the `unique` constraint itself is case-sensitive, like the team's). Create the row on first login.
- `onboarding_path` is required: `cv_upload` if the profile came from a CV import, otherwise `derja_detailed`.
  `literacy_level` is required: default `literate`.
- Consent: the form has a required checkbox; on save set `consent_version='1.0'` and `consent_given_at=now()`.
- Saving a profile replaces the candidate's skills, experiences, educations and desired occupations in one transaction.
- A fresh Supabase project has no skills or occupations: `scripts/seed_dev.py` adds ~30 skills (`SK-9001`...)
  and ~10 occupations (`OC-9001`...). The `9xxx` codes never collide with the team's real list.

## Design system (approved Mahara mockups)

- Colors: primary teal `#0F6E5C` · accent gold `#C6923F` with text `#241300` (main button only, never white
  text on it) · bg `#FAFAF7` · surface `#FFFFFF` · text `#1A1A1A` · text-secondary `#5B6B66` ·
  border `#E4E1D8` · danger `#C62828` (errors only).
- Fonts: **Outfit** 600/700 for headings and the "Mahara" wordmark, **Work Sans** for everything else. Text 13-16px.
- Layout (responsive web app, no bottom tab bar):
  - below 1024px: 56px top bar (teal logo tile + "Mahara", hamburger) and a 300px slide-out drawer (shadcn Sheet).
  - 1024px and up: 240px teal sidebar (active item: light fill + 3px gold right border) and a 72px top bar (page name on the left; from Session 2, the user's initials avatar
    and name on the right with a small menu containing "Se déconnecter").
  - Nav items: Accueil, Offres, Candidatures, Formation, Profil. Only Profil is built for now; the others
    show "Bientôt disponible".
- Components: shadcn/ui restyled with these colors, lucide-react icons, radius 10, pills 999.
  One gold button per screen, touch targets at least 44px, French `aria-label` on icon buttons.
- There are no mockup files in the repo: this Design system section is the only UI reference.

## Conventions

- **All keys and settings live in one file: `employee-module-wp6/.env`**, which I fill in myself. It is git-ignored
  (`employee-module-wp6/.gitignore` has `/.env`). Never create other `.env` files, never commit it, never print its
  values, and never ask me to paste them in the chat. If a value is missing, tell me the variable name and I'll add it.
  Keep `employee-module-wp6/.env.example` up to date with the same names and placeholder values (that one is committed).
  - Backend reads it with pydantic-settings, path computed from the code (`Path(__file__).resolve().parents[2] / ".env"`),
    so it works whatever folder you start from.
  - Frontend reads it through Vite with `envDir: '..'` in `frontend/vite.config.ts`. Vite only exposes `VITE_` variables to
    the browser, so `DATABASE_URL` never reaches the frontend.
  - Names: `DATABASE_URL`, `SUPABASE_URL`, `CORS_ORIGINS`, `APP_ENV` (backend); `VITE_SUPABASE_URL`,
    `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_API_BASE_URL` (frontend).
- Google Client ID/Secret are not env vars: they live in the Supabase dashboard (Authentication → Providers).
- **Commit messages:** `type(wp6): short summary` (team style, e.g. `feat(wp6): add google login`).
  Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`. Never mention "session" in a commit message.
- Code in English, UI text in French. Each endpoint gets at least one pytest.
- Fonts load from Google Fonts (needs internet); that's fine for now.
- **Every session ends the same way:** `pytest` and `npm run build` pass → both servers run and I've checked the
  feature in the browser → update "Current status" below and add a line to "Session log" → write
  `employee-module-wp6/docs/sessions/0N-<name>.md` (what was built, env var names added, decisions,
  known issues, what the next session should do first) → commit → `git push origin feature/wp6-employee-module`.

## Session plan

1. Foundation: schema, backend `/health`, app shell.
2. Google login.
3. Profile API + Profil page (seed skills and occupations).
4. Profile form (3 steps, create + edit).
5. CV import (PDF/DOCX → prefilled form).
6. Later: switch to the team Supabase project.

Each session's details come in its prompt; don't build ahead.

## Session log

*(one line per completed session, appended in order; never reorder or delete entries)*

- 2026-09-30 · Session 1, foundation: `db/schema.sql` (10 tables, 24 governorates, run on my project), FastAPI
  `/api/v1/health` + models, Vite/React app shell (sidebar ≥1024px, drawer below) with placeholder pages.
  See `docs/sessions/01-foundation.md`.
- 2026-09-30 · Session 2, Google login: PKCE sign-in with supabase-js, `/auth/callback`, route guard, sign-out in
  sidebar/drawer/top-bar menu, `api()` helper (Bearer token, 401 → sign out); backend `app/auth.py` (ES256 via JWKS,
  users row by lower-cased email) and `GET /api/v1/me`. See `docs/sessions/02-auth.md`.

## Current status

*(overwrite this section each session; it's the single source of truth for "where are we")*

- Last completed: Session 2, Google login (sign-in, sign-out, route guard, `GET /api/v1/me`), checked in the browser
- Next up: Session 3, profile API + Profil page (seed skills and occupations)
- Supabase: my own project with `db/schema.sql` applied and Google provider enabled; Redirect URLs include
  `http://localhost:5173/auth/callback` (switch to the team project in Session 6)
- `.env` has all names from `.env.example` set (`DATABASE_URL`, `SUPABASE_URL`, `VITE_SUPABASE_URL`,
  `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_API_BASE_URL`); no new names in Session 2
- Auth pieces to reuse: backend `Depends(get_current_user)` → `CurrentUser(user, name)`; frontend `api<T>(path)`
  in `src/lib/api.ts`, `useAuth()` in `src/lib/auth-context.ts`
- Known issues / TODO: rotate the Google OAuth client secret (shared in chat in Session 2) and the database password
  (shared in chat in Session 1, possibly again in Session 2); keep `%` encoded as `%25` in `DATABASE_URL`
