# Production Readiness Backlog

This backlog captures the highest-priority work identified in the engineering
readiness audit. Status reflects evidence available during that audit; it does
not imply that a task is assigned or tracked in an external issue tracker.

## In progress

- **P2.3 — Candidate data lifecycle and recovery:** authenticated JSON ZIP export
  and deletion/redaction with 30-day purge are implemented. Production backup
  configuration and restore evidence remain unverified, and legal review must
  confirm the retained-record boundary.

## To do

### P0 — Security and account safety

- [ ] **P0.1 — Enforce production JWT secret configuration** (S)
  Reject startup outside development when `JWT_SECRET` is absent, weak, or the
  built-in default. Keep secrets out of source control.
- [x] **P0.2 — Enforce account deactivation** (S)  
  Reject authentication for inactive users and define how existing tokens are
  invalidated when an account is disabled. Active status is checked against the
  database on authenticated requests, so linked-account tokens stop working
  immediately after deactivation.
- [x] **P0.3 — Protect authentication endpoints from abuse** (M)  
  Add configurable rate limits for login, signup, verification, and password
  reset, and test the limits. Apply migration
  `20261101010000_auth_rate_limit_buckets.sql` before deploying.
- [x] **P0.4 — Resolve ministry MFA and provisioning claims** (M-L)  
  Implement and verify the advertised second factor and controlled admin
  provisioning, or remove unsupported security claims from the product UI.
  The unsupported invitation/MFA claims were removed; MFA itself is not
  implemented.

### P1 — Deployment and reliable core workflows

- [ ] **P1.1 — Define production process topology** (M)
  Document and deploy the API, frontend, notification worker, and market
  ingestion worker as managed processes with restart policy, logs, and health
  monitoring. The worker commands currently exist separately from API startup.
- [ ] **P1.2 — Verify PostgreSQL migrations and critical workflows** (L)
  Run migrations and integration tests against PostgreSQL, including account
  creation, offer publishing, applications, and market ingestion.
- [ ] **P1.3 — Provide a working documented STT configuration** (M)
  Make the default `WHISPER_MODEL` compatible with `faster-whisper`, or document
  and validate the conversion/setup required before the voice workflow is used.
  Do not rely on an unlicensed model for commercial use.
- [ ] **P1.4 — Implement dependency-aware readiness checks** (M)
  Report actual database/migration and required service status; expose worker
  health and alert on stalled or repeatedly failing jobs. Do not equate imported
  modules with operational modules.
- [ ] **P1.5 — Verify external service integrations** (M)
  Exercise configured LLM chat and 768-dimensional embeddings, email delivery,
  private object storage, and STT in a deployment-like environment. Record
  provider failures and recovery behavior.

### P2 — Verification, data governance, and user experience

- [ ] **P2.1 — Add integration coverage for unverified workflows** (L)
  Add tests for training-provider flows, mock interviews, notification retries,
  market worker retries, and readiness checks. Keep provider fakes explicit and
  separate from live-provider verification.
- [ ] **P2.2 — Add a frontend release check** (M)
  Install dependencies in CI, run `npm run build`, and add suitable frontend
  route/API and accessibility checks.
- [ ] **P2.3 — Define candidate data lifecycle and recovery** (L)
  Document and implement account deletion/export, retention rules, backup
  schedules, and tested restoration for personal and uploaded data. The API now
  supports candidate JSON ZIP export and deletion with immediate deactivation,
  redaction, and a 30-day purge. The approved targets are RPO 24 hours and RTO
  8 hours. Production backup configuration/retention and a verified restore
  remain deployment work; legal review must confirm the currently retained
  records and the 30-day boundary. See
  `docs/data-lifecycle-and-recovery.md`. Apply
  `20261102000000_candidate_data_lifecycle.sql` before deploying.
- [x] **P2.4 — Complete or remove placeholder frontend controls** (M)
  Connect search and notifications to real features or remove/label controls
  that currently only display placeholder behavior. Removed the inert search
  field and always-empty notification popover; neither was wired to a service.

### P3 — Maintainability and scale

- [ ] **P3.1 — Replace hard-coded module registration status** (M)
  Derive module status from meaningful checks and configured capabilities.
- [ ] **P3.2 — Review legacy data artifacts and model boundaries** (M)
  Establish whether the tracked SQLite database is needed, then document or
  remove it through an approved repository change. Review the legacy/shared ORM
  boundaries for schema drift.
- [ ] **P3.3 — Establish performance baselines** (M-L)
  Load-test matching, analytics, and ingestion with representative data; add
  pagination or query optimization where measurements justify it.

## Completed

- [x] **P0.2 — Immediate account deactivation:** linked candidate, ministry, and
  employer access is rejected on subsequent requests; login is also denied.
- [x] **P0.3 — Configurable auth rate limiting:** per-IP counters are stored in
  PostgreSQL and shared across API instances. Login (including Google OAuth
  start/callback), signup, email verification, and password-reset endpoints
  return `429` with `Retry-After` when over limit.
- [x] **P0.4 — Correct ministry access messaging:** UI now says access is role
  restricted and that MFA is unavailable; it no longer claims invitation
  provisioning or 2FA.
- [x] **P2.4 — Removed placeholder topbar search and notification controls.**
- [x] **P2.3 — Candidate export/deletion API implemented.** The full P2.3
  remains open until legal review and production backup/restore verification.
- [x] **Engineering readiness audit completed.** Findings and scorecard were
  summarized in the audit response; no application code was changed.
- [x] **Backend test suite run:** `python -m pytest -q` — 77 passed after the
  security changes.
- [x] **Frontend production build:** `Set-Location front; npm.cmd run build` —
  passed after `npm.cmd ci`.

## Priority guide

- **P0:** Security and account-safety work required before exposing real users or
  sensitive data.
- **P1:** Production deployment and core workflow reliability.
- **P2:** Verification, privacy lifecycle, and user-facing completeness.
- **P3:** Improvements best prioritized using measured usage and operating data.
