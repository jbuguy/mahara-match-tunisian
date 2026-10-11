# WP4 and WP6 Integration Plan

## Goal

Deliver one candidate-to-employer journey on the root platform: an employer creates and publishes a validated offer in WP4; WP3 can match it; a candidate discovers it and applies in WP6; the employer reviews the application and records a decision. Both modules use the root FastAPI runtime, WP1's PostgreSQL schema and contracts, and the same identity and authorization rules.

## Current baseline

- The root API already mounts WP4's employer agent, WP4 voice transcription, WP6 routes, WP3 routes, and application routes in `backend/app/main.py`.
- WP4 drafts and publishes `NormalizedJobOffer` records to WP1's `job_offers` and `job_offer_skills` tables, and stores conversational drafts in `employer_draft_sessions`.
- WP6 profile, CV import, assistant, and voice features are integrated into the root app. Its documented next step is reconciling its former persistence with WP1's shared models.
- An application router already supports candidate list/create and employer decisions. Creating an application requires a published offer and a current WP3 match; duplicate applications return 409.
- WP1 defines shared models and contracts for employers, offers, candidates, applications, and hiring feedback.
- Authentication remains a key integration boundary: WP4 currently authenticates employers through `/employers/signup` and `/employers/login` with an employer-scoped token; WP6 uses the platform's Google identity and user-scoped token. The plan consolidates authorization around platform users and roles without breaking existing local flows until migration is complete.

## Implementation started

The root backend now organizes the shared application workflow into `backend/app/repositories/applications.py` (database reads and writes), `backend/app/services/applications.py` (lifecycle rules and WP1 contract mapping), and `backend/app/applications.py` (HTTP request/authentication/error adapter). Other work packages can call the service functions with the canonical SQLAlchemy session rather than reimplementing application behavior.

WP6's `backend/app/models.py` now exports compatibility aliases to WP1's canonical account, candidate, identity, reference, and taxonomy ORM models. Its HTTP schemas and routes retain their existing shapes, while the root WP3-to-WP6 candidate lookup also uses WP1's `Candidate` mapping. This removes WP6's duplicate ORM table definitions from the integrated runtime; the separate WP6 schema file remains historical and must not be applied.

The candidate journey now has an authenticated `GET /api/v1/me/offers` feed assembled from published, unexpired WP1 offers, skill requirements, current WP3 scores, and the candidate's existing application state. WP6's Offres page refreshes matches before submitting an application, then Candidatures shows its submitted applications and status. WP4's Candidatures navigation now opens an employer-owned application inbox and can record shortlist, reject, or hire decisions through the shared lifecycle service. Reads of candidate identity data in that inbox now write WP1 audit-log events. The WP6 frontend defaults to the root API on port 8000; the root also keeps the previous `/api/v1/auth/google` OAuth entry URL working for that frontend.

Per the current user direction, the implementation is continuing with the cross-module journey; no WP4 schema migration/reconciliation work is included in this scope.

Frontend production builds were attempted for WP4 and WP6 but could not start because the local frontend dependencies are not installed (`tsc` is unavailable in both packages). No tests were run.

## Integration principles

1. WP1 owns schema, migrations, enums, and public data contracts. No package-local duplicate canonical tables or schemas.
2. The root `backend` is the only runtime/API surface and `migrations/` is the only migration sequence.
3. Candidate and employer IDs come from the authenticated principal and database relationships, never from trusted client input.
4. Candidate PII stays in `candidate_pii`; employer access to it is limited to an application and audited access. Matching receives non-PII profile data.
5. An offer is not visible to candidates until it is validated and published. Candidate application actions and employer status updates are authorized by role and ownership.
6. Keep WP4's AI drafting and WP6's profile assistant independent. They share the configured backend LLM facilities and WP1 contracts, not prompt state or user-facing sessions.

## Work sequence

### 1. Lock the shared contracts and behavior

- Confirm the WP1 contract versions and fields used by both packages: `CandidateProfile`, `NormalizedJobOffer`, `ApplicationCreate`, `ApplicationRead`, `ApplicationStatusUpdate`, and `HiringFeedback`.
- Document the application status lifecycle, allowed employer transitions, candidate visibility, and whether a candidate can withdraw. Reject unsupported transitions consistently.
- Agree on offer visibility, required fields, occupation/governorate normalization, and handling when WP3 has not yet produced a current match.
- Decide how legacy employer password accounts transition to the platform user identity and role model. Preserve account ownership and employer data; do not silently create a second employer record for the same account.

**Exit:** a reviewed contract and authorization table with no package-specific competing definitions.

### 2. Reconcile persistence and identity

- Audit WP6's `backend/app/models.py`, profile services, root integration adapter, and historical `db/schema.sql` against `mahara_data.db.models` and the ordered root migrations.
- Replace WP6 duplicate ORM definitions and direct persistence with WP1 shared models, while keeping its HTTP response shape stable where practical.
- Confirm all WP4 reads/writes use WP1 models and that draft sessions remain separate workflow state, linked to the canonical employer row.
- Make employer lookup consistently resolve the authenticated platform user to exactly one `Employer`; candidate lookup resolves the user to exactly one `Candidate`.
- Add any required schema change only as a new ordered migration; never apply the historical WP6 schema as a second source.

**Exit:** a clean root database can be migrated once and serves both modules with no duplicate canonical tables or identity records.

### 3. Unify authentication and access control

- Define the platform token claims and role checks for candidate and employer requests.
- Migrate employer login/signup to the agreed platform identity flow (or provide an explicit, time-bounded compatibility exchange) and remove reliance on a distinct employer-only token after clients have migrated.
- Apply consistent 401/403/404 behavior, ownership checks for draft sessions/offers/applications, and role restrictions for every route.
- Ensure WP4 voice transcription and draft endpoints, WP6 profile/application endpoints, and employer application review all use the same principal resolution.
- Add audit events for employer reads of candidate identity/contact information and hiring decisions.

**Exit:** one identity maps to one platform user and role-bound module access; cross-account resource access is denied.

### 4. Complete the candidate-to-employer API journey

- WP4: finish/review offer generation, edit, review-before-publish, publish idempotency, and ownership checks against WP1 offer contracts.
- WP3 boundary: ensure only published offers enter matching and that match results identify the exact offer revision/version used.
- WP6: expose candidate-facing published offer discovery/details and application list/create/withdraw behavior as agreed; derive candidate identity from the token.
- WP4 employer workflow: list applications for employer-owned offers, show only permitted candidate information after application, and record valid status decisions plus structured hiring feedback.
- Return shared contract payloads with stable error responses; avoid returning internal draft/session data across the module boundary.

**Exit:** the complete workflow succeeds from publishing an offer through application and employer decision, with authorization enforced at each step.

### 5. Integrate the user interfaces

- Keep WP4 employer and WP6 candidate experiences as role-specific areas of the platform; use shared platform navigation, API base configuration, session handling, and error conventions.
- Add candidate offer search/detail/apply and application status screens to WP6 only after the API lifecycle is settled.
- Add employer application inbox/detail/decision screens to WP4, including clear explanations of candidate fit and what identity details are visible.
- Keep French/Derja language support, accessible labels, low-literacy copy, and responsive layout consistent with the existing WP6 constraints.

**Exit:** a candidate and employer can complete the journey through the UI without separate login/session surprises.

### 6. Verify the integrated platform

- Migration checks: fresh database migration, repeatability where supported, and ORM/schema parity for touched tables.
- Contract checks: valid and invalid WP1 payloads for offers, candidate profiles, applications, and feedback.
- API integration checks: publish → matching availability → candidate discovery → apply → employer decision; include missing match, duplicate apply, unpublished offer, invalid status transition, and unauthorized ownership cases.
- Identity/privacy checks: candidate cannot see another candidate's application; employer cannot see an unrelated offer/application; candidate PII is hidden before application and audited when revealed.
- UI checks: both role flows, expired/invalid session, empty states, validation errors, and responsive behavior.
- Run package and root checks in CI; keep model/API keys and database credentials server-side.

**Exit:** all checks pass against the canonical root runtime and a clean migrated database; operational setup and known limitations are documented.

## Suggested milestones

| Milestone | Deliverable | Depends on |
|---|---|---|
| M1: Contract and identity decisions | Approved lifecycle, role matrix, migration path | — |
| M2: Shared persistence | WP6 and WP4 use WP1 models and root migrations | M1 |
| M3: Secure API workflow | Offer, matching, application, decision endpoints integrated | M2 |
| M4: Connected UI | Candidate and employer screens use shared auth/API | M3 |
| M5: Release validation | End-to-end checks, migration validation, docs | M4 |

## Decisions to record before implementation

- Whether employer sign-in moves to Google/platform SSO or retains passwords behind the platform identity service.
- Final application statuses and transition rules, including withdrawal and rejection/acceptance semantics.
- The precise PII subset visible to an employer after applying and the audit event fields/retention.
- Whether publishing an offer triggers matching synchronously, asynchronously, or through an explicit WP3 refresh.
- Whether WP4 and WP6 remain separate frontends during the first integrated release or are mounted under one platform shell.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| WP4 and WP6 currently use different token flows | Decide migration before UI connection; use a temporary explicit token exchange only if required. |
| Historical WP6 persistence diverges from WP1 | Compare models/migrations first; use additive root migrations and data-preserving reconciliation. |
| Applications require current matches | Define refresh and stale-match behavior; return a clear actionable response when no current match exists. |
| Candidate PII leaks through employer views | Separate profile and identity payloads; gate PII on application, audit reads, and test pre/post application access. |
| Offer edits invalidate match/application context | Define offer revision behavior and recompute or invalidate current matches on material edits. |
