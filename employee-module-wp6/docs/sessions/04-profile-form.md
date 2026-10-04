# Session 4: Profile form

Date: 2026-09-30 · Branch: `feature/wp6-employee-module`

Goal: the candidate creates and edits their profile by hand at `/profil/modifier`. CV import is not part of this session.
Added during the session at my request: the Google profile photo (with an own photo as an option) and a pass on speed.

## What was built

**The form: `frontend/src/components/profile/`**
- `ProfileForm.tsx`: one component, three steps, used for create and edit.
  - Props: `initialValues` (optional starting values), `fromCv` (sent as `from_cv`), `cancelTo`, and
    `onSaved(profile, { photoFailed })`.
  - A step indicator on top ("Étape 2 sur 3" + three bars). Each bar can be tapped; going forward checks the steps in between.
  - A bottom bar that stays visible on phones (`sticky bottom-0`): "Annuler" on step 1, "Précédent" after that, "Suivant", and on
    step 3 the gold "Enregistrer".
  - Saving: `PUT /api/v1/me/profile`, then the photo if it changed.
    - A 422 is mapped from `detail[].loc` to the field, and the form jumps to that step.
    - A 409 or a network error shows a message in the bottom bar.
- `steps.tsx`:
  - Step 1, Infos: photo, nom complet, téléphone, gouvernorat (native select), niveau d'études.
  - Step 2, Compétences: search, then one card per skill with four level buttons (Débutant, Intermédiaire, Avancé, Expert)
    and "Retirer". New skills go on top, at level 2.
  - Step 3, Expérience et préférences:
    - experiences (poste, employeur, then either dates or "Durée en mois")
    - métiers souhaités (search, 10 at most)
    - disponible à partir du
    - langues with a level
    - "À propos de moi" (500 characters, with a counter)
    - the required consent checkbox
- `form-values.ts`:
  - The form state types, and `normalizeValues`, `profileToFormValues` and `toProfileIn`.
  - The checks (`validateStep`) and the mapping of server errors (`serverErrors`, `stepOfError`).
  - `ProfileFormStart` is what a CV draft should give. Experiences and languages may leave out `key`/`mode`.
- `ReferenceSearch.tsx`: a search box with 250 ms debounce. Results are a list of 48px buttons ("Ajouter" / "Ajouté"),
  and Enter doesn't submit the form.
- `PhotoPicker.tsx`: the current photo, "Changer la photo" (camera or gallery) and "Utiliser la photo Google".
- `fields.tsx` / `field-attrs.ts`: label, "(facultatif)", hint, error with icon, 48px inputs with 16px text, and a select with a chevron.

**Checks (French, next to the field)**
- Required: nom complet, téléphone, gouvernorat, consent.
- Phone: a Tunisian number, 8 digits starting 2-9, optionally with `+216` or `00216` in front. Spaces, dots and dashes are allowed.
- Experience: the poste is required, the end date can't be before the start date, and the duration is a whole number of months.
- Languages: a language must be chosen, and each only once.
- Errors show once the candidate has tried to leave a step, then update as they type. Focus goes to the first field in error.

**Pages**
- `pages/ProfilFormPage.tsx`: "Créer mon profil" or "Modifier mon profil". It uses the profile the Profil page hands over in
  the link state, or loads it on a direct visit. A new profile starts with the Google name.
- `pages/ProfilPage.tsx`:
  - "Profil enregistré." after a save. It isn't shown again after a reload.
  - An alert if the photo failed.
  - It uses the saved profile handed back by the form instead of loading it again.
  - The photo on the identity card.
- `lib/labels.ts`: skill level 3 is now "Avancé" (was "Confirmé").
- `components/layout/AppShell.tsx`: `<ScrollRestoration />`, so a new page opens at the top.

**Photo**
- Database: `candidate_pii.photo bytea`. It's in `schema.sql` (in the table, plus `add column if not exists` for existing databases)
  and was applied to my project. Approved in the chat as a DB column, rather than Supabase Storage.
- Backend: `app/services/photo.py` and `app/routers/photo.py`.
  - `GET /api/v1/me/photo` returns the `image/jpeg`, or 404.
  - `PUT` (multipart `file`) accepts only JPEG (checked by its first bytes) up to 300 KB, and returns 204. It returns 404 if
    there's no profile yet.
  - `DELETE` returns 204.
  - `ProfileOut.has_photo` is added. Saving the profile never touches the photo.
- Frontend:
  - `lib/image.ts` crops to a centred square and makes a 256×256 JPEG in the browser (a few KB).
  - `lib/photo.ts`: `useUserPhoto()` gives the photo to show (own photo, else the Google `avatar_url` at 256px, else initials),
    and `setCustomPhoto()` updates it everywhere after a save.
  - `components/Avatar.tsx` falls back to initials if the image fails, and uses `referrerPolicy="no-referrer"` for Google.
  - Shown in the top bar, sidebar, drawer, Profil card and the form.
- The consent sentence now also lists "ma photo".

**Speed** (every database round trip costs about 150-190 ms from here)
- `get_profile` is a single SQL query with `json_build_object` / `json_agg`, instead of 7.
- `save_profile`:
  - one query checks all codes (was 3)
  - the identity row is an upsert (was a read, then a write)
  - one statement clears the four lists on an edit (was 4)
  - nothing is deleted on a first save
- `last_login_at` is written at most every 15 minutes (`LAST_LOGIN_EVERY`). It used to cost an UPDATE and a COMMIT on every request.
- `/reference/*` only checks the token (`get_token_claims`), with no user lookup.
- `db.py`: `gssencmode=disable` saves one round trip per new connection.
- `main.py`: at start-up, 3 connections are opened and the login keys fetched in a background thread.
- Frontend:
  - governorates and search answers are cached for the visit
  - `getMe` and `getProfile` share a call that's already running (StrictMode doubles effects in dev)
  - the profile is handed between Profil and the form instead of being loaded again
- Measured through the app with the real database (averages):

  | Request | Before | After |
  |---|---|---|
  | `GET /me/profile` | 1 442 ms | 915 ms |
  | `GET /me` | 1 376 ms | 816 ms |
  | skill search | 1 012 ms | 425 ms |

  Saving went from about 32 statements plus a full reload to about 16.

**Tests:** 38 (10 new)
- `tests/test_photo.py`: upload and read back, the profile save keeps the photo, delete, non-JPEG → 415, too large → 413,
  no profile → 404, and 401 without login for all three methods
- `test_me.py`: a recent `last_login_at` isn't rewritten
- The existing profile tests pass unchanged on the single-query `get_profile`

## Env var names

No new names.

## Decisions

- **No form library:** plain `useState`. A step's errors are computed from the values (live) once the candidate has tried to leave it.
- **Native inputs:** plain `<select>`, `<input type="date">` and a native checkbox, styled with the Mahara tokens, instead of new
  shadcn components. On phones this gives the system pickers, and it avoids the shadcn CLI re-adding the `cn` package.
- **Step 2 defaults:** a new skill starts at level 2 (Intermédiaire); a new language starts at "Intermédiaire".
- **Hidden data is kept:** fields the form doesn't show (educations, `years_experience`, experience descriptions, e-mail) are
  sent back unchanged, so a save doesn't erase them.
- **Experience period:** dates or duration. The mode not chosen is sent as null, so a CV experience with both keeps its dates.
- **Consent box:** already ticked in edit mode (it was given before). The backend still needs `consent: true` on every save.
- **Photo timing:** the photo goes up after the profile, because a new profile must exist first. If only the photo fails, the
  profile is still saved and `/profil` says so.
- **Photo while loading:** the Google photo shows while the own photo loads. A small localStorage hint shows initials
  instead for people who have their own photo, so the Google photo doesn't flash before it.
- **`last_login_at`:** throttled to 15 minutes. Session 2 said "every request"; it cost 2 round trips each time.
- **`pool_pre_ping`:** kept (one round trip per request). Without it, a connection the pooler dropped would fail a request.

## Known issues

- **Remaining slowness:** most of what's left is network distance to the Supabase pooler (~190 ms per round trip; a simple
  request still needs 3-5). Switching to the team project (Session 6) may be faster or slower depending on its region.
- **Consent wording:** it's my draft and needs a team check. `consent_version` is still `1.0`.
- **Stuck reload on Windows:** uvicorn `--reload` got stuck once, and the old code kept serving (new routes gave 404).
  Touching `app/main.py` made it reload. Restart the backend if that doesn't help.
- **Dev server after rewriting a file:** Vite served a half-written module once ("does not provide an export named …").
  Touch the file or reload the page.
- **Browser check:** the form and photo flows were tested in a headless browser with fake API answers, and then by me with
  my Google account.
- **Bundle size:** the JS bundle is still over 500 kB (supabase-js). This is fine locally.

## What Session 5 should do first

1. Read CLAUDE.md and all files in `docs/sessions/`.
2. Build the backend CV import: pypdf / python-docx → a draft in the `ProfileFormStart` shape (codes plus `label_fr` /
   `title_fr` for skills and occupations). Keep it to one or two queries, because of latency.
3. On `/profil/importer-cv`, upload the file, then render `<ProfileForm initialValues={draft} fromCv />`. Nothing is saved
   until "Enregistrer".
