# Session 5: CV import

Date: 2026-09-30 · Branch: `feature/wp6-employee-module`

Goal: the candidate imports a CV (PDF or DOCX) and gets the profile form already filled in. Nothing is saved until
"Enregistrer". The form's steps and the profile API are unchanged, apart from using the existing `from_cv` flag.

This write-up and the CLAUDE.md update were added after the session: the code was finished and checked in the browser,
but the documentation step was missed at the time.

## What was built

**Backend: `app/services/cv_import.py`** (pypdf 6.19, python-docx 1.2)
- Reading the file:
  - `file_kind()` accepts a file only when the extension **and** the first bytes agree (`%PDF-` for `.pdf`, a zip
    header for `.docx`). An old `.doc` or a renamed file is refused.
  - PDF: text of the first 10 pages (`MAX_PDF_PAGES`). A fix joins letters that kerning splits
    ("T echnologies" → "Technologies").
  - DOCX: the page header (Word templates often put the name and contacts there), then paragraphs and tables in reading
    order; a merged cell is read once.
  - Fewer than 20 non-space characters, or a broken / password-protected file → `UnreadableCv`.
- Text is compared with `fold()` (lower-case, no accents, one character for one) and `words()` (folded words padded
  with spaces, so `" vente "` doesn't match inside `"eventail"`).
- `split_sections()` splits the CV by headings (Expérience, Formation, Compétences, Langues, and "other" headings such
  as Loisirs or Projets). A heading is a short line with no digits that starts with a known word; "Compétences : Vente,
  Excel" keeps what follows the colon.
- What's pulled out:
  - **Name**: the first of the first 5 lines that looks like a name (skips "Curriculum Vitae", contact lines,
    headings); ALL CAPS becomes Title Case.
  - **Email**: first match, lower-cased.
  - **Phone**: a Tunisian number (8 digits starting 2-9, optional `+216` / `00216`, spaces, dots or dashes allowed),
    written back as `22 345 678` or `+216 22 345 678`. A year range like `2019-2020` is not taken for a phone.
  - **Skills**: every validated catalog skill whose `label_fr` or one of its `alt_labels` appears anywhere in the CV,
    in the order they first appear, with level 2, source `cv`, no confidence. The catalog is read in **one query**
    (`load_skills`).
  - **Unmatched words**: items of the Compétences and Langues sections that match no skill ("Photoshop",
    "Lecture de plans"), 30 at most, with labels like "Technologies:" and "(courant)" removed.
  - **Educations**: lines naming a diploma (doctorat, ingénieur, master/mastère, licence, BTS, baccalauréat/bac, BTP,
    CAP), with the field of study ("Licence en gestion" → "Gestion"), the school (a part mentioning université,
    institut, ISET, lycée…) and the year (the latest year on the line). A next line about the same diploma completes
    it instead of adding a second one. Read from the Formation section, or from everywhere except Expérience when the
    CV has no such heading. `education_level` is the highest diploma found.
  - **Experiences**: under the Expérience heading, each line is a job ("Vendeur - Monoprix", "Vendeur chez Monoprix",
    "Développeuse full-stack NOVATECH" with the employer in capitals, "Stage : …" → "… (stage)"). Dates on the line
    ("03/2019", "mars 2019", "2019 - aujourd'hui") become `start_date` / `end_date` as `YYYY-MM-01` and are removed
    from the title; a line with only dates attaches to the job next to it. Bullets and sentences below a job become
    its description.
- `build_draft()` returns `CvImportOut`: `{draft, unmatched_words}`.

**Backend: `POST /api/v1/me/cv`** (`app/routers/cv.py`)
- Multipart field `file`. Only checks the token (`get_token_claims`, no user lookup), because nothing is saved.
- 413 over 5 MB (`MAX_CV_BYTES`; the read stops at 5 MB + 1 byte), 415 if not a real PDF/DOCX, 422 with
  `detail` = "Nous n'avons pas pu lire ce CV, remplissez le formulaire" for a scanned or broken file.
- The file is only held in memory for the request; it isn't stored anywhere.
- `app/schemas.py`: `CvSkill`, `CvExperience`, `CvEducation`, `CvDraft`, `CvImportOut`. The draft uses the form's own
  shape: `''` means "not found", experience dates are strings, educations are the same as `EducationIn`.

**Seed:** `scripts/seed_dev.py` has 14 more skills, `SK-9033`…`SK-9046` (JavaScript, TypeScript, Python, Java, PHP,
React, Node.js, Spring Boot, SQL, MongoDB, Git, API REST, développement mobile, intelligence artificielle), so
developer CVs match too. It was run again on my project (46 `SK-9…` skills).

**Tests:** 52 in total (14 new) in `tests/test_cv_import.py`
- Two fictional sample CVs in `tests/fixtures/`: `sample_cv.pdf` (Amira Ben Salah, welder, Sfax) and
  `sample_cv.docx` (Mohamed Trabelsi, sales, contacts in a table, "Curriculum Vitae" first line). They're made by
  `python -m tests.fixtures.make_samples`; the PDF is written by hand because there's no PDF-writing library in the
  stack.
- Parsing without a database: both samples field by field, a developer CV layout (year before the job, company in
  capitals, school on the diploma line), kerning fix, accent-free skill matching, year range vs phone, dates removed
  from the job line.
- Endpoint without a database: wrong types (`.txt`, `.doc`, fake `.pdf`, a PDF named `.docx`) → 415, over 5 MB → 413,
  blank PDF → 422 with the French message, broken DOCX → same message, no login → 401.
- Endpoint with the real database (rolled back): both samples return a draft with catalog skills (level 2, source
  `cv`), experiences and educations, and no `candidates` row is created.

**Frontend**
- `src/lib/api.ts`: `CvDraft`, `CvImport`, `MAX_CV_BYTES`, and `importCv(file, onProgress)`. It uses
  `XMLHttpRequest` because `fetch` can't report upload progress; a 401 signs out like `request()` does.
- `src/pages/CvImportPage.tsx` at `/profil/importer-cv` (replaces the placeholder):
  - a drop zone ("Déposez votre CV ici", PDF or Word, 5 Mo max) with the gold "Choisir mon CV" button
  - type and size are checked in the browser first, with the same French messages as the server's 415/413
  - progress bar "Envoi… N %", then "Lecture du CV…" while the server reads it
  - a scanned CV shows the server's message and a "Remplir le formulaire" button
  - then the session 4 `ProfileForm` with `initialValues` from the draft and `fromCv`, under a gold notice
    "Vérifiez les informations avant d'enregistrer", a summary ("Trouvé dans votre CV : 3 compétences,
    2 expériences, 1 diplôme."), the unmatched words ("Non reconnu : … Cherchez une compétence proche à l'étape 2.")
    and "Choisir un autre fichier"
- `src/components/profile/cv-draft.ts`: `draftToFormStart(draft, savedProfile, googleName)`.
- `src/pages/ProfilPage.tsx`: "Importer mon CV" on the empty state (already there) and, new, as an outlined button
  next to the gold "Modifier" on the filled profile. Both hand the profile over in the link state.

## Env var names

No new names.

## Decisions

- **Importing on top of an existing profile adds, never erases:** what's saved stays; the CV only fills empty fields
  (email, phone, education level) and adds skills, jobs (same title + employer) and diplomas (same level + year) that
  aren't there yet. A new profile uses the CV's name, or the Google name if the CV has none.
- **`from_cv`:** saving from the import page sends `from_cv: true`, so `onboarding_path` becomes `cv_upload` (also on
  an existing profile, as decided in Session 3).
- **Draft shape = form shape:** the backend returns `''` for "not found" and string dates, so the page passes the draft
  to the form with almost no conversion.
- **Skills are searched in the whole CV,** not only under Compétences (a welder's CV often names the trade only in the
  job line). Unmatched words come only from Compétences / Langues, otherwise every line would be "unmatched".
- **Content checked, not just the name:** extension and first bytes must both match; the browser checks too, so a wrong
  file gets its message before the upload.
- **415 before 422:** type and size are checked before reading the text, so those tests need no database.
- **Scanned CVs:** no OCR (not in the stack). They get the French message and a way to the empty form.
- **Speed:** one query per import (the skills catalog); the login check doesn't touch the database.

## Known issues

- **Not extracted yet:** governorate (e.g. "Sfax" in the sample), desired occupations, availability, summary, and the
  Langues section as form languages (languages only show up as skills, e.g. "Français"). The candidate fills these in
  the form.
- **Best effort parsing:** unusual layouts (two columns, text in images, tables used for layout) can give odd titles or
  miss jobs; the candidate corrects them in the form before saving.
- **Name:** taken from the first lines; a CV that starts with an address or a job title can give a wrong name.
- **Uploads aren't cancellable:** leaving the page during the upload lets the request finish in the background.
- **Bundle size:** the JS bundle is 723 kB (supabase-js mostly). Fine locally.

## What Session 6 should do first

1. Read CLAUDE.md and all files in `docs/sessions/`.
2. Reuse the CV import's matching for free text → codes: `fold()` / `words()` and `load_skills()` /
   `find_skills()` in `app/services/cv_import.py`, and `draftToFormStart()` as an example of merging a draft into the
   form's starting values.
3. Follow the Session 6 prompt (the Session plan in CLAUDE.md is updated there).
