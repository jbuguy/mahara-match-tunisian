# CLAUDE.md: Mahara WP6 Employee Module, project memory

This file lives at `employee-module-wp6/CLAUDE.md` (uppercase name, so Claude Code finds it on any OS). Read it first, every session, before doing anything else. Then read **all** files in
`employee-module-wp6/docs/sessions/` (if the folder exists yet), in order, for the history of what's been built and why.
Scope and sequencing are already decided in this file and in each session prompt: don't re-derive them.

## Project

Mahara Match: Tunisian national employment platform. The team shares one GitHub repo
(`jbuguy/mahara-match-tunisian`); each person works independently on their own branch.
This branch builds the candidate side (WP6, Employee Module). **Current scope:**

1. **Authentication**: sign in with Google.
2. **Candidate profile**: the candidate creates it by filling a form **or** by importing a CV (PDF/DOCX),
   then can view and edit it.
3. **Profile assistant**: an AI chat agent ("Assistant Mahara") that asks one question at a time, understands
   answers in French, Tunisian Derja (Latin or Arabic letters) or Arabic, typed or spoken, and fills the profile
   form for the candidate to review and save.

Everything else (offers, applications, roadmap) waits until this is done. UI is in French; users may have
low literacy, so keep copy short, buttons big, and a text label on every icon.

## Constraints

- Keep WP6-specific implementation inside `employee-module-wp6/`; shared database migrations live in root `migrations/`.
- Use PostgreSQL only. `data-layer-wp1/` and its `mahara_data` package define the shared schema and contracts; do not add a hosted BaaS dependency or a second canonical copy of shared data.
- Branch `feature/wp6-employee-module`. Never commit to `main`.
- PostgreSQL runs from the repository's Docker Compose configuration. Google OAuth is an external identity provider; application data and Mahara sessions remain on our own backend/PostgreSQL.
- Local only: no production deploy config. Groq is the only external AI service.
- Context is cleared between sessions. Every session ends with the app **working locally**. If a session
  runs long, cut scope, not the test-and-document step at the end.

## Stack: don't add libraries beyond this list without asking

- **Backend** (`employee-module-wp6/backend/`, port **8006**): Python 3.12+ (dev machine uses 3.14), FastAPI, SQLAlchemy 2
  (shared models are preferred for shared entities), psycopg 3, pydantic-settings, PyJWT[crypto], httpx, python-multipart, pypdf,
  python-docx, pytest, and `httpx2` for tests only (Starlette's `TestClient` needs it).
- **Frontend** (`employee-module-wp6/frontend/`, port **5173**): Vite + React + TypeScript, Tailwind CSS v4,
  shadcn/ui, lucide-react, React Router v8. Plain `fetch` + `useState`, no extra
  state or form libraries. Packages that shadcn installs itself are approved too (clsx, tailwind-merge,
  class-variance-authority, radix-ui, tw-animate-css).
- **Auth + DB:** PostgreSQL plus direct Google OAuth. Google OAuth only: no passwords, no SMS, no signup form. The backend verifies Google's ID token and issues a short-lived Mahara JWT.
- **AI (Session 6+):** Groq API (free plan) through the official `groq` Python package, called **only from the
  backend**. Chat model from `GROQ_MODEL` (default `openai/gpt-oss-120b`, an open-weights model), speech-to-text
  `whisper-large-v3-turbo` (same `GROQ_API_KEY`, no extra env var). Free-plan limits: about 30 requests and 8,000 tokens per minute for the chat model,
  so keep each request small. Voice recording uses the browser's built-in MediaRecorder (no extra package).

### Version traps (your training data is older than these)

- React Router **v8**: import from `react-router`. `react-router-dom` no longer exists.
- Tailwind **v4**: `@import "tailwindcss";` + `@theme {}` in CSS, `@tailwindcss/vite` plugin.
- Google ID tokens are verified with Google's JWKS and audience set to `GOOGLE_CLIENT_ID`; never accept a browser token without server-side verification.
- Mahara access tokens use HS256, issuer `mahara-match`, audience `mahara-match-wp6`, and a 30-minute expiry. `JWT_SECRET` must have at least 32 random bytes and remain backend-only.
- Local PostgreSQL uses `postgresql+psycopg://...`; never expose database credentials to the browser.

## How it works (keep it this simple)

- **Login:** the frontend redirects to `/api/v1/auth/google`. The backend performs Google's OAuth code exchange, maps the verified email to the PostgreSQL `users` row, and issues a Mahara token to the callback page.
- **Data:** everything else goes through the FastAPI backend with `Authorization: Bearer <access_token>`.
  The backend checks the token, finds the user by email, and reads/writes the tables with the models in `app/models.py`.
- Backend layout: `app/main.py` (app + routers), `app/config.py`, `app/db.py`, `app/models.py` (SQLAlchemy tables),
  `app/auth.py`, `app/routers/` (thin), `app/services/` (logic), `app/schemas.py` (request/response models), `tests/`.
  PostgreSQL migrations live in root `migrations/`; the WP6 schema file is an idempotent compatibility supplement while shared-schema reconciliation is completed.
- **CV import** is done inside this backend: read the text with pypdf / python-docx, pull out email, phone,
  skills that match the `skills` table, education and experience lines, and return a **draft** the candidate
  reviews in the form. Nothing is saved and the file isn't stored until they press "Enregistrer".
- **Profile assistant** (`app/services/assistant.py`, `app/routers/assistant.py`): stateless. The frontend sends the
  recent conversation + the current form draft; the backend asks Groq for JSON `{reply, updates, asking, done}`, validates it,
  maps skill/job/governorate names to codes with the same matching as the CV import, and returns the reply and the
  field updates. A skill or job that isn't in our lists triggers one more small Groq call whose reply stays on it
  (close items from our lists as suggestions, or "Ignorer"), so the chat doesn't move on. The assistant **never saves
  the profile and never ticks consent**: the candidate reviews the form and presses "Enregistrer". The AI key and the
  prompts stay on the backend. If Groq is down, missing a key or rate-limited, the assistant says so politely and the
  form keeps working.
- **Voice input** (Session 7): the browser records with MediaRecorder, the backend sends the audio to Groq's
  `whisper-large-v3-turbo` (same `GROQ_API_KEY`, no forced language so French and Derja both work) and returns the text.
  The transcript always goes into the chat's text box first, for the candidate to fix and send; the audio is never stored.

## Data model (our `db/schema.sql`; names match the team's schema so we can switch later)

`db/schema.sql` is the source of truth for keys and types; this section is the summary.

```text
governorates    code (pk, e.g. TN-11), name_fr, name_ar                  -- 24 rows inserted by schema.sql
users           id, email (unique), role='candidate', preferred_language='fr', last_login_at
candidates      id, user_id (unique: one profile per user), onboarding_path, literacy_level, governorate_code, education_level,
                years_experience, languages (jsonb [{code, level}]), summary, available_from,
                consent_version, consent_given_at
candidate_pii   candidate_id (pk), full_name, email, phone, photo (bytea, own 256px JPEG; null = Google photo)
                                                               (identity kept apart from the profile)
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
- A fresh development database has no skills or occupations: `scripts/seed_dev.py` adds ~45 skills (`SK-9001`...)
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
  - Names: `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `JWT_SECRET`, `API_BASE_URL`, `FRONTEND_URL`, `CORS_ORIGINS`, `APP_ENV`, `GROQ_API_KEY`, `GROQ_MODEL` (backend);
    `VITE_API_BASE_URL` (frontend). `GOOGLE_CLIENT_SECRET`, `JWT_SECRET`, and `GROQ_API_KEY` must never get a `VITE_` prefix.
- Google Client ID/Secret are backend environment variables. Configure the local redirect URI as `http://localhost:8006/api/v1/auth/google/callback`.
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
6. Profile assistant, text chat (AI agent fills the form).
7. Profile assistant, voice input (speak instead of typing).
8. Integrate WP6 with the shared PostgreSQL schema and WP1 contracts.

Each session's details come in its prompt; don't build ahead.

## Session log

*(one line per completed session, appended in order; never reorder or delete entries)*

- 2026-09-30 · Session 1, foundation: `db/schema.sql` (10 tables, 24 governorates, run on my project), FastAPI
  `/api/v1/health` + models, Vite/React app shell (sidebar ≥1024px, drawer below) with placeholder pages.
  See `docs/sessions/01-foundation.md`.
- 2026-09-30 · Session 2, Google login: PKCE sign-in with supabase-js, `/auth/callback`, route guard, sign-out in
  sidebar/drawer/top-bar menu, `api()` helper (Bearer token, 401 → sign out); backend `app/auth.py` (ES256 via JWKS,
  users row by lower-cased email) and `GET /api/v1/me`. See `docs/sessions/02-auth.md`.
- 2026-09-30 · Session 3, profile API: `scripts/seed_dev.py` (32 skills, 12 occupations), `/reference/*` search,
  `GET/PUT /api/v1/me/profile` (one transaction, 422 per unknown code), DB tests in rolled-back transactions,
  Profil page (empty state + full view), placeholders `/profil/modifier` and `/profil/importer-cv`.
  See `docs/sessions/03-profile-api.md`.
- 2026-09-30 · Session 4, profile form: 3-step `ProfileForm` at `/profil/modifier` (create + edit, plain state, French
  errors next to fields, server 422 mapped to fields, sticky Précédent/Suivant bar), `initialValues` + `fromCv` props for
  CV import; Google photo by default + own photo (`candidate_pii.photo`, `/api/v1/me/photo`); speed work (profile read in
  1 query, fewer save statements, no reloads between Profil and the form, cached reference data).
  See `docs/sessions/04-profile-form.md`.
- 2026-09-30 · Session 5, CV import: `app/services/cv_import.py` (pypdf / python-docx → name, email, phone, catalog
  skills, educations, experiences; unmatched Compétences/Langues words), `POST /api/v1/me/cv` (415/413/422, saves
  nothing, file not kept), 2 sample CVs in `tests/fixtures/`, `/profil/importer-cv` (drop zone, progress, prefilled
  form with `fromCv` → `cv_upload`), 14 tech skills added to the seed. See `docs/sessions/05-cv-import.md`.
- 2026-09-30 · Session 6, profile assistant (text): `app/services/assistant.py` + `POST /api/v1/me/assistant/chat`
  (Groq `openai/gpt-oss-120b`, JSON mode, `{reply, updates, asking, done}`, names → codes, unknown skills/jobs clarified
  with suggestions or "Ignorer", French errors 503/429/502, saves nothing); "Remplir avec l'assistant" on the Profil
  empty state and `/profil/modifier`: side panel from 1280px, bottom sheet below, fields fill in with a gold highlight
  and the form follows the question's step. See `docs/sessions/06-assistant-chat.md`.
- 2026-09-30 · Session 7, assistant voice input: `POST /api/v1/me/assistant/transcribe` (Groq `whisper-large-v3-turbo`,
  no forced language, webm/ogg/mp4/wav read from the first bytes, 2 MB max → 413, 415, French errors, audio not stored);
  "Parler" in the chat (MediaRecorder, red button with pulsing dot and counter, stops at 60 s, "Annuler"), transcript
  added to a full-width growing text box for the candidate to fix and send. See `docs/sessions/07-assistant-voice.md`.

## Current status

*(overwrite this section each session; it's the single source of truth for "where are we")*

- Last completed: Session 7, voice input for the assistant ("Parler" → MediaRecorder → Groq `whisper-large-v3-turbo`
  → text in the chat's text box, never sent by itself); marked done by me
- Next up: replace WP6's duplicate persistence with shared PostgreSQL models/contracts and finish cross-package integration.
- Voice pieces to reuse: backend `app/services/voice.py` (`audio_kind()` from the first bytes, `transcribe()`),
  `POST /api/v1/me/assistant/transcribe`; frontend `useVoiceRecorder(onText)` in `src/components/assistant/`
- PostgreSQL: use the root Compose database and shared migrations. Google OAuth credentials are configured in `.env`; the redirect URI is `http://localhost:8006/api/v1/auth/google/callback`.
- `.env` has all names from `.env.example` set, including `GROQ_API_KEY` and `GROQ_MODEL` (added in Session 6;
  backend only). `APP_ENV` must be `dev` or `development` for the seed script to run
- Assistant pieces to reuse (voice feeds the transcribed text into the same chat):
  - backend `app/services/assistant.py`: `assistant_turn()` (one chat turn), `_complete()` (one JSON-mode Groq call with
    the French error messages), `get_groq_client` (FastAPI dependency, 503 without a key), `candidate_language()`
  - frontend: `useAssistantChat(formRef)` (`send(text)`, `retry()`) and `<AssistantChat>` in `src/components/assistant/`;
    `ProfileFormHandle` (`getValues`, `applyUpdates(updates, asking)`, `focusForm`) on `ProfileForm`'s `ref`;
    `src/components/profile/assistant-updates.ts` (draft for the AI, merging its updates)
- Auth pieces to reuse: backend `Depends(get_current_user)` → `CurrentUser(user, name)` (needs the users row), or
  `Depends(get_token_claims)` when only a valid Mahara token is needed (no database); frontend `api<T>(path)` in `src/lib/api.ts`,
  `useAuth()` in `src/lib/auth-context.ts`
- Profile pieces to reuse:
  - backend: `ProfileIn` / `ProfileOut` (now with `has_photo`) in `app/schemas.py`; unknown codes → 422 in FastAPI's
    own shape (`loc` + `input`)
  - CV import (`app/services/cv_import.py`): `fold()` / `words()` for accent-free matching, `load_skills()` (catalog in
    one query), `find_skills()`; the draft (`CvDraft`) uses the form's shape
  - frontend: `ProfileForm` (`src/components/profile/`), `ProfileFormStart` (starting values; experiences and languages
    may leave out `key`/`mode`), `profileToFormValues`, `toProfileIn`, `draftToFormStart` (CV draft + saved profile); photo via `useUserPhoto()` / `setCustomPhoto()` in
    `src/lib/photo.ts`, `<UserAvatar>` in `src/components/Avatar.tsx`; French labels in `src/lib/labels.ts`
- Speed: every database round trip costs ~150-190 ms (network distance to the pooler), so keep statements per request
  low (one-query reads, batched writes) and don't refetch what a previous page already has
- Tests: 144; profile, photo, reference and CV-endpoint tests use the real database inside a rolled-back transaction (skipped if
  unreachable); assistant and voice tests mock Groq (no network, no key needed)
- Groq free plan: a chat turn is ~1,000 tokens (~1,700 when a name isn't in our lists), so about 7 turns a minute under
  the 8,000 tokens/minute limit; past it the chat shows "Un instant, réessayez dans quelques secondes." with "Réessayer"
- Known issues / TODO: keep `%` encoded as `%25` in `DATABASE_URL`; consent wording (now lists the photo) still needs
  a team check; uvicorn `--reload` on Windows often misses changes (new routes/fields missing): restart the backend
  after backend edits