# Observatory audit

Audit scope: repository inspection plus the local PostgreSQL service. No application code was changed.

## 1. Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 18 with TypeScript in [package.json](../package.json) |
| Frontend build/test | Vite, Vitest, jsdom, and Testing Library in [package.json](../package.json) |
| Chart library | None declared or currently implemented in [package.json](../package.json). The admin page uses HTML/CSS metric cards, bars, and tables in [src/marketplace.tsx](../src/marketplace.tsx). |
| Backend framework | FastAPI with Uvicorn in [backend/requirements.txt](../backend/requirements.txt) |
| ORM | SQLAlchemy 2 in [backend/app/models.py](../backend/app/models.py) and [backend/app/database.py](../backend/app/database.py) |
| Migration tool | Alembic in [backend/alembic.ini](../backend/alembic.ini) and [backend/migrations/versions/](../backend/migrations/versions/) |
| Backend tests | pytest and HTTPX TestClient in [backend/tests/](../backend/tests/) |

## 2. Locations

### Persistence

- `candidate_profiles.location`: nullable free-text `String(120)` in [backend/app/models.py](../backend/app/models.py), entered without a controlled list.
- `job_offers.location`: required free-text `String(120)` in [backend/app/models.py](../backend/app/models.py), entered without a controlled list.
- `training_courses.location`: optional free-text `String(120)` in [backend/app/models.py](../backend/app/models.py), entered without a controlled list.
- There are no governorate, municipality, city, latitude, longitude, or normalized-location fields for any of these entities.

### Location inputs

- Candidate profile location, normal editor: [src/workspaces.tsx](../src/workspaces.tsx), `Lieu de résidence`, using the shared `ProfileTextField`; it is a free-text input.
- Candidate profile location, CV review editor: [src/workspaces.tsx](../src/workspaces.tsx), `Lieu de résidence`, a free-text input.
- Candidate profile location inside the profile body used by the CV/profile flow: [src/components/ProfileBuilder.tsx](../src/components/ProfileBuilder.tsx) also has free-text experience location under `Lieu (facultatif)`; this is experience-location data, not the top-level candidate residence field.
- Job offer location: [src/workspaces.tsx](../src/workspaces.tsx), offer verification/publishing form, `Lieu`; free-text.
- Training course location: [src/marketplace.tsx](../src/marketplace.tsx), course create/edit form, `Lieu (obligatoire en présentiel/hybride)`; free-text.
- Public/location search:
  - candidate discovery uses a free-text location filter in [src/GuestDiscovery.tsx](../src/GuestDiscovery.tsx);
  - public job discovery also has a free-text location filter in [src/GuestDiscovery.tsx](../src/GuestDiscovery.tsx).

### Current values

The local database was queried directly. It currently contains:

| Entity | Distinct location values |
|---|---|
| Candidate profile | `NULL` (1 row) |
| Job offer | no rows |
| Training course | no rows |

Therefore the live database currently has no persisted municipality/governorate strings that can be counted and no observable location duplicates. The seeded data is the repository’s available location reference:

- Candidate seed values in [backend/scripts/seed_demo_data.py](../backend/scripts/seed_demo_data.py): Tunis, Sfax, Sousse, Bizerte, Ariana, Monastir, Nabeul, Kairouan, and Gabès.
- Job-offer seed values in [backend/scripts/seed_demo_data.py](../backend/scripts/seed_demo_data.py): Tunis, Sfax, Sousse, Ariana, Monastir, and Nabeul.
- Course seed values in [backend/scripts/seed_demo_data.py](../backend/scripts/seed_demo_data.py): Tunis, Sfax, and `Remote`.
- Synthetic job-offer values in [backend/app/synthetic_data.py](../backend/app/synthetic_data.py): Tunis, Sfax, Sousse, Kairouan, `Gabes`, and Bizerte. `Gabes` is an unaccented spelling variant of Gabès.

Across the seed definitions, excluding `Remote`, 9 distinct governorate/city names are present: Tunis, Sfax, Sousse, Bizerte, Ariana, Monastir, Nabeul, Kairouan, and Gabès/Gabes. All 9 can be matched to Tunisian governorates and are also municipality/city names matching their same-named governorates. `Remote` is non-geographic and does not map. Thus the repository seed corpus has **9 governorate-mappable values**, **9 values containing a matchable city/governorate name**, and **1 non-geographic value**.

## 3. Application status history

`job_applications` has both a current-status column and a dedicated history table.

- Current status column: [backend/app/models.py](../backend/app/models.py).
- History model: `JobApplicationStatusHistory` in [backend/app/models.py](../backend/app/models.py), with application, actor, previous status, new status, and timestamp.
- Initial application records create a history row with `from_status = NULL` and `to_status = submitted` in [backend/app/marketplace.py](../backend/app/marketplace.py).
- Candidate withdrawal appends `from_status -> withdrawn` in [backend/app/marketplace.py](../backend/app/marketplace.py).
- Employer status changes append `from_status -> to_status` in [backend/app/marketplace.py](../backend/app/marketplace.py).
- History retrieval is exposed through `GET /employer/applications/{application_id}/history` in [backend/app/marketplace.py](../backend/app/marketplace.py).

Existing status values, from [backend/app/models.py](../backend/app/models.py):

`submitted`, `reviewing`, `shortlisted`, `interview`, `interview_completed`, `offer_made`, `hired`, `rejected`, `withdrawn`.

Allowed employer transitions are defined in [backend/app/marketplace.py](../backend/app/marketplace.py):

- `submitted` -> `reviewing`, `shortlisted`, `interview`, `hired`, or `rejected`.
- `reviewing` -> `shortlisted`, `interview`, `hired`, or `rejected`.
- `shortlisted` -> `reviewing`, `interview`, `hired`, or `rejected`.
- `interview` -> `interview_completed`, `offer_made`, `hired`, or `rejected`.
- `interview_completed` -> `offer_made`, `hired`, or `rejected`.
- `offer_made` -> `hired` or `rejected`.
- Closed states (`hired`, `rejected`, `withdrawn`) cannot be changed.
- Employers cannot set `withdrawn`; only the candidate withdrawal endpoint can.

## 4. Candidate age information

No candidate birth date, age, or age band field exists in the candidate profile model or schemas. Repository-wide searches of [backend/app/models.py](../backend/app/models.py) and [backend/app/schemas.py](../backend/app/schemas.py) found no such field. Only general account timestamps may be queried as account-registration age, not candidate age.

## 5. Course enrollment completion

`course_enrollments` has `created_at` and `updated_at`, but no dedicated completion date or completion timestamp in [backend/app/models.py](../backend/app/models.py). A completion is therefore inferable only approximately from `updated_at`.

Enrollment statuses in [backend/app/models.py](../backend/app/models.py):

- `enrolled`
- `completed`
- `withdrawn`

The status transition endpoint updates `status` and the shared `updated_at` timestamp in [backend/app/marketplace.py](../backend/app/marketplace.py).

## 6. Skills

Skills are stored as JSON arrays of strings, not normalized relational skill rows:

- Candidate skills: `candidate_profiles.skills` JSON array in [backend/app/models.py](../backend/app/models.py).
- Job-offer required/preferred skills: JSON arrays in [backend/app/models.py](../backend/app/models.py).
- Training-course skills: `training_courses.skills` JSON array in [backend/app/models.py](../backend/app/models.py).
- Skill normalization trims entries, removes blanks, deduplicates case-insensitively for API/schema writes in [backend/app/schemas.py](../backend/app/schemas.py), but legacy or database-entered variants can remain.

The live database has no candidate skills to rank. For the repository seed corpus, the following counts combine candidate-profile and job-offer skill strings, excluding course fixtures that would require dynamic dates to parse:

| Rank | Skill string | Count | Notes |
|---|---|---:|---|
| 1 | SQL | 12 |  |
| 2 | Python | 11 |  |
| 3 | Stakeholder Management | 6 |  |
| 4 | Docker | 5 |  |
| 5 | React | 5 |  |
| 6 | Documentation | 5 |  |
| 7 | Power BI | 4 |  |
| 8 | Excel | 4 |  |
| 9 | Business Analysis | 4 |  |
| 10 | PostgreSQL | 4 |  |
| 11 | Figma | 3 |  |
| 12 | Data Analysis | 3 |  |
| 13 | JavaScript | 3 |  |
| 14 | CSS | 3 |  |
| 15 | Marketing Digital | 3 |  |
| 16 | SEO | 3 |  |
| 17 | Analytics | 3 |  |
| 18 | Machine Learning | 3 |  |
| 19 | DevOps | 3 |  |
| 20 | CI/CD | 3 |  |
| 21 | Linux | 3 |  |
| 22 | Swift | 3 |  |
| 23 | Kotlin | 3 |  |
| 24 | Flutter | 3 |  |
| 25 | Mobile UI | 3 |  |
| 26 | Cybersecurity | 3 |  |
| 27 | Network Security | 3 |  |
| 28 | FastAPI | 2 |  |
| 29 | UX Research | 2 |  |
| 30 | Design System | 2 |  |

Obvious duplicate groups in seeded data are limited or absent; no `Excel`/`MS Excel` pair occurs in the seed. Potential normalization aliases should be established before ministry aggregation: `SQL` variants, `JavaScript`/`JS`, `Power BI`/`Microsoft Power BI`, `Figma`/`Figma Design`, and `React.js`/`ReactJS` can be canonically mapped even though the current corpus does not contain them.

## 7. `fetchAdminIndicators`

Frontend function: [src/auth.ts](../src/auth.ts), calling `GET /admin/indicators`.

Backend computation: [backend/app/marketplace.py](../backend/app/marketplace.py):

- Candidate registrations in the optional date range.
- Organisation count in the optional date range.
- Published, non-duplicate offers are counted from records whose status is `published` in the range.
- Applications grouped by current status and total applications in the range.
- Closed applications = hired + rejected + withdrawn.
- Declared hire rate = hired / closed applications, multiplied by 100; UI labels it as employer-declared.
- Top 10 required skills, deduplicated case-insensitively within each offer, from published offers.
- Published courses, filtered to `published`.
- Active/enrolled course enrollments.
- Completed course enrollments.

Reuse for the new observatory:

Likely direct reuse:
- `published_job_offers` as the open/platform-demand numerator only after the offer-open/closed semantics are added.
- `applications_total` and `applications_by_status` as aggregate application/funnel inputs.
- `top_skills` as platform skill demand.
- `published_courses` and course completion/enrollment figures as training KPIs.
- `hired_applications` and `closed_applications` may support the declared placement rate, with the existing honest wording.

Currently reused conservatively:
- `hire_rate_percent` cannot itself establish placement or insertion; it is a platform/application outcome using closed applications.
- Candidate registrations are account creation counts, not an active-candidate count.
- The endpoint does not expose offer location, employer activity dates, time-to-hire, youth age bands, or training-to-job outcomes.

## 8. World Bank and AgriData knowledge documents

Storage:

- `knowledge_documents.content` is plain searchable text (`Text`) and `document_metadata` is JSON in [backend/app/knowledge_base.py](../backend/app/knowledge_base.py).
- World Bank and AgriData normalized observations are converted to one annual text document per source by `build_series_document` in [backend/app/ingest_labour_data.py](../backend/app/ingest_labour_data.py).
- The generated content format is:

  `Title — annual observations`
  `Country: ...`
  `Indicator: ...`
  `Methodology: ...`
  `Annual observations: YYYY: value unit; YYYY: value unit.`

- `document_metadata` contains source ID, methodology, period start/end, observation count, retrieval timestamp, licence, and licence URL for ingested series.
- Normalized records and ingestion handling are in [backend/app/data_pipeline.py](../backend/app/data_pipeline.py).
- World Bank observations originate from the JSON Indicators API in [backend/app/data_pipeline.py](../backend/app/data_pipeline.py).
- AgriData observations originate from an Excel workbook and are located by the first row containing `emploi`; annual headers are parsed in [backend/app/data_pipeline.py](../backend/app/data_pipeline.py).

Reliability:

- World Bank yearly values are structurally reliable once ingested because the API normalizer validates four-digit years and numeric values.
- AgriData yearly values are structurally reliable only if the workbook keeps numeric annual headers and an `emploi` row; the parser currently requires annual headers and reads the first worksheet.
- The database stores only rendered prose for yearly observations. Values are therefore parseable by a robust `YYYY: numeric value` regex, but there is no structured yearly row table. They should ideally be read from normalized JSONL records or a dedicated time-series table, not reparsed by charts.

## 9. Select/combobox component and RTL

- A reusable native `<select>` wrapper exists as `Select` in [src/components/ui.tsx](../src/components/ui.tsx).
- Many forms bypass it and use `<select className="input">` directly.
- Native HTML select supports keyboard operation, but it is not a searchable combobox.
- No reusable combobox/autocomplete implementation was found.
- No Arabic option labels or RTL direction test was found in the location controls. The global font includes `Noto Sans Arabic`, but that does not provide RTL behaviour in [src/styles.css](../src/styles.css).
- Direction must be set explicitly with `dir="rtl"` and RTL-aware layout if Arabic governorate names/options are added; the current reusable `Select` does not implement this.

## Prioritized schema gaps blocking observatory KPIs

1. **Active candidates:** add explicit candidate activity state and activity timestamp, or a derived/recorded definition based on profile and platform events. Current registration count is not active-candidate share.
2. **Open positions:** add reliable offer lifecycle timestamps and/or explicit open/closed timestamps. Current status supports `published`, `paused`, `closed`, `expired`, and `archived`, but the admin endpoint cannot distinguish whether a published offer is currently open without closed/expiry date semantics.
3. **Declared placement rate:** add an outcome/placement fact tied to the hire status, employer declaration timestamp, and agreed cohort. `hired / closed applications` is only a current application-stage ratio, not placement into employment.
4. **Median days to hire:** add application timestamp transitions sufficient to measure each application’s submitted-to-hired duration. History exists, but a normalized funnel/time analytics query or dedicated hire-at timestamp is still needed.
5. **Youth share:** add explicit candidate date of birth or a privacy-preserving age band and provenance field. The current candidate schema has neither.
6. **Training-to-job rate:** link course enrollment completion and subsequent employer hire for the same candidate, with a declared outcome and observation date. `course_enrollments` and `job_applications` are separate and currently lack a completed/enrolled-to-job cohort mapping.
7. **Funnel stages:** add or retain immutable timestamps for every funnel stage; application history supplies transitions, but data tests and aggregate queries must enforce complete stage provenance and offer aliases for deduplicated candidates/offers.
8. **Candidates per open position by governorate:** normalize governorate and municipality fields for candidates and offers, add governorate codes, and preserve free text as source-label fallback. No usable normalized location structure exists now.
