# Ministry and employer prototype: backend follow-up plan

The ministry and employer screens now use real user actions and existing API data. Prototype scenario toggles and demo-only values must stay out of the production UI. The remaining prototype features need the following backend contracts before they can be presented as live functionality.

## Implemented in the current work

- Official salary benchmark read contract, with a minimum sample size of 15, explicit source period/publisher, sparse-data suppression, and only explicitly deposited national or Grand Tunis aggregates. Percentile fields are optional source metadata; median rows are never combined to invent a regional median.
- Ministry labour-market aggregates for published offer demand and jobseeker desired-occupation supply, including same-length prior-period comparison, versioned ratio definition, and suppression of non-zero candidate cohorts below k=10.
- Audited CSV export of those same protected aggregates, including spreadsheet-formula-safe text cells.
- Paginated/filtered employer offer (`GET /api/v1/employer/offers/page`) and application (`GET /api/v1/employer/applications/page`) endpoints, plus audited publish/close/reopen transitions for employer-owned offers (`PATCH /api/v1/employer/offers/{id}/status`). Reopening an expired offer requires an explicit future expiry or clearing the expiry.
- Full normalized offer editing, explicit archive rules (closed offers only; no unresolved submissions, views, shortlists, interviews, or offers), archive filtering, and audit events.
- Candidate-controlled employer contact consent, consent-gated interview invitations, and a durable SMTP notification outbox with delivery status, retry tracking, and cancellation on consent revocation.
- CSV/XLSX dataset upload with size/row bounds, private object storage, preview, row validation, explicit partial-import confirmation, hash verification, ingestion history, and expiry cleanup.
- Privacy-protected PDF report export alongside the audited CSV export.
- Required reject rationale in the ministry UI and audit payload; create/edit operations for skills and occupations now also record an audit entry.
- Durable official-market refresh queue, idempotency keys, overlap prevention, a `SKIP LOCKED` worker, bounded JSON feed validation, and refresh control in the ministry ingestion view. Deployment still needs the authoritative feed URL/token and a supervised worker process.

The salary threshold is set to 15 to match the prototype's stated sparse-data threshold. Confirm this with the data governance owner before production rollout.

## Priority 0: needed for truthful, production use

### Territorial salary benchmark

The endpoint is implemented at `GET /api/v1/employer/market/salaries`. The data ingestion contract accepts `extra.sample_size`, `extra.p25_tnd`, `extra.p75_tnd`, and an explicit `extra.region` of `national` or `grand_tunis` for aggregate rows. Rows without verifiable sample size are suppressed.

The employer-authorized endpoint is `GET /api/v1/employer/market/salaries?occupation_code=...&governorate_code=...&period_start=...&period_end=...`.

- Return currency, percentile/range, data period, source, sample size, and suppression state.
- Suppress precise results below the approved minimum sample threshold and explain the sparse-data state.
- Permit an explicit broader-region request (for example, Grand Tunis) and return that region in the response.
- Keep raw salary records and employer identities out of the response.
- Do not display the prototype's salary figures, source dates, or SIVP incentive claims until backed by maintained official data and an approved policy source.

### Live regional demand and tension analytics

Implemented at `GET /api/v1/admin/analytics/labour-market`; aggregated CSV is available from `GET /api/v1/admin/analytics/labour-market/export.csv`.

Extend the ministry analytics contract or add an aggregated endpoint for demand by governorate, occupations ranked by tension, and period comparison.

- Return only aggregate counts and suppression metadata, with the privacy threshold applied server side.
- Include the period and definition/version for each rate so charts cannot imply unsupported precision.
- Reuse the existing aggregate skill-gap endpoint where appropriate; do not expose candidate-level records.

### Safe refresh and ingestion lifecycle

Implemented: `POST /api/v1/admin/market/refresh` enqueues a durable job with an idempotency key; duplicate requests return the existing job, and overlapping official refreshes return `409`. Run the worker separately with `python -m app.features.ministry.worker`; PostgreSQL `FOR UPDATE SKIP LOCKED` allows multiple worker processes safely. The worker accepts a `MarketDatasetSubmission` JSON document from the configured feed, validates it, imports rows through the shared normalization pipeline, and records counts/errors in ingestion history.

Configure `MINISTRY_MARKET_FEED_URL`, optionally `MINISTRY_MARKET_FEED_TOKEN`, and run the worker as a supervised deployment process. Production feed URLs must use HTTPS. The upstream response shape is `{"dataset": {...}, "records": [...]}`, bounded to 10 MiB and 5,000 records. No ANETI URL is hard-coded because the authoritative feed URL and authentication details are not present in this repository. The worker also cleans expired uploads when no official feed is configured.

File uploads use private S3-compatible storage. Production deployment must provide `S3_BUCKET` and credentials (plus endpoint/region as needed), run the new database migration, and ensure the bucket has private access and lifecycle/backup settings appropriate for retained confirmed datasets. Preview objects are removed after two hours if not confirmed.

## Priority 1: complete the prototype's operating workflows

### Employer offer lifecycle

Offer status transitions and paginated offer/application reads are implemented in the employer API. Candidate interview invitations remain blocked on a candidate-consent flow and notification delivery/outbox service; no invitation will be marked as sent until delivery is verifiable.

- Offer editing, close/reopen transitions, explicit archive eligibility, ownership checks, audit events, server-side status filters, pagination, and status counts are implemented.
- Interview invitation requires recorded candidate consent, a future meeting time and timezone, and configured SMTP. The durable outbox reports queued/sending/sent/failed/cancelled state and retries temporary failures. `sent` means the SMTP server accepted the message; it does not confirm inbox delivery.
- Production deployment must configure SMTP and run `python -m app.features.employer.notifications` as a supervised worker. Monitor failed rows and retry exhaustion; the frontend displays delivery state instead of assuming an invitation was delivered.

### Ministry suggestion and occupation editing

Skill and occupation create/edit actions are now audited, and rejection requires an official rationale stored in the audit record. Semantic duplicate candidates and similarity scores remain unavailable until a versioned duplicate-detection service and evidence source are added.

The core taxonomy write endpoints already support creating/editing/validating skills and occupations, and suggestion approve/merge/reject. Build audited edit forms against those contracts before showing the prototype's full ROME comparison and occupation-skill editor.

- Add a clear detail response for suggestions with evidence, source records, and duplicate candidates if semantic similarity is supported by the service.
- Return similarity scores only when the backend has computed and versioned them; the current suggestion contract has no duplicate score.
- Rejection reason is required and stored in the audit record. A request-for-more-information workflow still needs a ministry policy and state transition.

### Ministry exports and audit

The aggregate CSV and PDF exports are implemented from the same privacy-protected aggregates; audit filtering and pagination were already available.

- Role-protected aggregate CSV and PDF exports are implemented and audited.
- Keep the export aggregated and apply the same privacy suppression as the analytics endpoint.
- Add filters and export pagination to audit history if the full audit log becomes too large for the current page-by-page viewer.

## Already available and now wired in the screens

- Employer offer sessions, chat/form draft generation, draft review, publish, offer listing, application listing/detail, and shortlist/hire/reject decisions.
- Ministry skill/occupation list and edit APIs, skill validation, suggestion approval/merge/rejection, market dataset listing/deposit, ingestion job listing/detail, skill-gap analytics, monitoring, and audit listing.

These screens should keep loading, empty, error, and forbidden states driven by API responses. The HTML prototypes' system-state selector and mock actions are design aids only and should not be shipped.
