# Session 3: Profile API and Profil page

Date: 2026-09-30 · Branch: `feature/wp6-employee-module`

Goal: the backend can read and save a candidate profile, and the Profil page shows it. The form and CV import are not part of this session.

## What was built

**Seed: `backend/scripts/seed_dev.py`**
- Run it from `backend/` with `python -m scripts.seed_dev`. It refuses to run unless `APP_ENV` is `dev` or `development`.
- It inserts 32 skills (`SK-9001`…`SK-9032`), all with status `validated`:
  - 22 hard skills: trades, office work, web development, and so on
  - 5 soft skills
  - 5 languages
- It inserts 12 occupations (`OC-9001`…`OC-9012`).
- Rows are upserted by `code` (`on conflict do update`), so running it twice is safe. It was run twice on my project.
- Each skill's `alt_labels` holds accent-free spellings and synonyms ("developpement web", "soudeur", "derja"). Search uses them, and CV import will too.

**Backend**
- `app/routers/reference.py` and `app/services/reference.py`. Every route requires login (router-level `Depends(get_current_user)`).
  - `GET /api/v1/reference/governorates` returns all 24, ordered by code.
  - `GET /api/v1/reference/skills?q=`:
    - searches only `validated` skills
    - matches `ILIKE` on `label_fr`, `code` and `alt_labels::text`, with `%` and `_` in `q` escaped
    - lists labels that start with `q` first, then sorts alphabetically, with a maximum of 20
  - `GET /api/v1/reference/occupations?q=` works the same way on `title_fr` and `code`.
- `app/routers/profile.py` and `app/services/profile.py`:
  - `GET /api/v1/me/profile` returns `ProfileOut`, or 404 `profile not found`.
    - It includes the name, email and phone from `candidate_pii`, the governorate object, and the languages.
    - It includes the skills (joined with their label and type), experiences, educations and desired occupations (with title and priority).
    - Order: skills by level (highest first) then label, experiences by newest start date, educations by newest graduation year, occupations by priority.
  - `PUT /api/v1/me/profile` takes `ProfileIn` and returns the saved `ProfileOut`. Everything happens in one transaction:
    - it creates or updates `candidates`
    - it upserts `candidate_pii`
    - it deletes and re-inserts the skills, experiences, educations and desired occupations
    - on any error it rolls back
- `app/schemas.py`:
  - reference output models
  - `ProfileIn`: `consent` must be `true`; `from_cv`, `full_name` (required), `email`, `phone`, the scalar candidate fields, `languages`, `skills`, `experiences`, `educations`, `desired_occupations`
  - `ProfileOut`
  - The allowed values reuse the tuples in `app/models.py` as `Literal[...]`.
  - Validation: duplicate codes in one request are rejected, and `end_date` can't be before `start_date`.
- Unknown governorate, skill or occupation codes give a **422 using FastAPI's own error shape**. One entry per bad code, for example `{"type":"unknown_code","loc":["body","skills",1,"code"],"msg":"unknown skill code","input":"SK-0000"}`. The form can handle both kinds of 422 the same way.
- Tests: 28 in total (19 new).
  - `tests/test_reference.py` covers:
    - the 24 governorates
    - accent-free search
    - deprecated skills are hidden
    - the 20-result limit
    - `%` taken literally
    - occupation search
    - 401 without a token
  - `tests/test_profile.py` covers:
    - 404 when there is no profile
    - create, including all fields and GET returning the same data
    - `from_cv` → `cv_upload`
    - a second save replaces everything with no duplicates (row counts checked, consent timestamp unchanged)
    - missing or false consent
    - unknown codes (all three reported, nothing saved)
    - duplicate skill codes
    - 401 without a token

**Frontend**
- `src/lib/api.ts`: the `Profile` types, plus `getProfile()`, which returns `null` on 404.
- `src/lib/labels.ts`: French labels for education levels, skill levels (1 Débutant, 2 Intermédiaire, 3 Confirmé, 4 Expert), languages and language levels, plus date formatting helpers. Reuse it in the form.
- `src/pages/ProfilPage.tsx` has four states:
  - loading
  - error, with a "Réessayer" button
  - empty: "Votre profil n'est pas encore créé", the gold "Créer mon profil" button (→ `/profil/modifier`) and the outlined "Importer mon CV" button (→ `/profil/importer-cv`)
  - full profile, with these parts:
    - the page title and the gold "Modifier" button
    - an identity card: initials, name, education · experience · availability, and email/phone/governorate lines with icons and screen-reader labels
    - "À propos", shown only if there's a summary
    - cards for Compétences (pills with the level), Expériences, Formation, Métiers recherchés and Langues (pills with the level); each card has an empty message
- `src/pages/placeholders.tsx`: `ProfilFormPage` and `CvImportPage` ("Bientôt disponible" and "Retour au profil"). Their routes are added in `main.tsx`.

## Env var names

No new names. `APP_ENV` now matters: the seed only runs when it's `dev` or `development`.

## Decisions

- **Tests use the real database:** SQLite can't run this schema (jsonb, `gen_random_uuid()`, check constraints). Each test runs in an outer transaction and the session uses `join_transaction_mode="create_savepoint"`, so the service's `commit()` only releases a savepoint and everything is rolled back at the end. Tests create their own skills and occupations with random `SK-T…` / `OC-T…` codes, so they don't depend on the seed. They're skipped if the database can't be reached. Authentication is overridden with `get_current_user`; the token checks are already covered in `test_me.py`.
- **`onboarding_path`** is set when the profile is created (`cv_upload` if `from_cv`, else `derja_detailed`). A later plain edit keeps it, so an imported profile isn't relabelled when it's corrected by hand. A later save with `from_cv: true` sets it to `cv_upload`.
- **Consent:** `consent_version='1.0'` and `consent_given_at` are set only on the first save; later saves keep the original timestamp. Every save still requires `consent: true`.
- **`literacy_level`:** `literate` on create if it isn't sent. On update, it's kept unless it's sent.
- **PII email** defaults to the login email when the form doesn't send one.
- **`languages`** are stored as `[{code, level}]`. `code` is ISO 639-1 (`ar`, `fr`, `en`…) and `level` is one of `basic | intermediate | fluent | native`, validated by Pydantic (there's no database check, so the team's schema is untouched). Language skills (`SK-9028`…) also exist in the catalog for CV matching and offers.
- **Desired occupation priority** defaults to the order in the list (1, 2…).
- **Codes:** only `validated` skills can be searched or saved.
- **Ids:** candidate, experience and education ids are generated in Python (`uuid4`), as with users.
- **Unknown codes return 422, not 400,** in the same shape as Pydantic errors (`loc` + `input`).
- **Simultaneous first saves:** if two first saves create the `candidates` row at once, the losing one gets 409 `profile changed, try again`.
- **Accent-free search:** it relies on `alt_labels`, because the `unaccent` extension would be a schema change.
- **Gold button:** the filled profile view's only main action is "Modifier", so that's the gold button there. In the empty state, it's "Créer mon profil".

## Known issues

- **Secret rotation** (Google OAuth client secret, database password) is still not confirmed done. Carried over from Sessions 1 and 2.
- **Filled profile not seen:** it can't be reached from the UI until Session 4's form exists. Only the empty state was checked in the browser. The filled view was built against the API types and passes `tsc`.
- **Test speed:** the database tests take about 30 s over the session pooler.
- **Stale backend:** a `uvicorn --reload` process left over from Session 2 was still on port 8006 but didn't serve the new routes (404). It was killed and restarted. If new routes return 404, restart the backend.
- **Bundle size:** the JS bundle is still over 500 kB (supabase-js). This is fine locally.

## What Session 4 should do first

1. Read CLAUDE.md and all files in `docs/sessions/`.
2. Ask whether the secrets have been rotated.
3. Build the 3-step form at `/profil/modifier`:
   - load with `getProfile()` (null → empty form)
   - search with `/reference/skills?q=` and `/reference/occupations?q=`, and fill the governorate list from `/reference/governorates`
   - save with `PUT /api/v1/me/profile` (body = `ProfileIn`, including the required consent checkbox)
   - show 422 errors from `detail[].loc` next to the matching field
   - go back to `/profil` after saving
4. Reuse `src/lib/labels.ts` for every select, so the labels match the Profil page.
