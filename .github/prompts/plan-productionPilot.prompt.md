## Plan: Production Pilot Application

Target a limited real-user pilot, not a public-scale launch. Deliver one deployable product around the critical loop: candidate account and profile → ranked real offers → application → employer review and decision. Preserve the proven WP2/WP4/WP6 implementations where useful, but make WP1 PostgreSQL models/contracts and the root server/frontend the production source of truth.

**Steps**

### Phase 1: Canonical Data and Identity
1. Inventory root SQL migrations, `mahara_data` ORM models, WP4 persistence, and WP6 schema/models. Define a migration-backed mapping for candidate identity/profile and employer identity/offers. The observed WP6 `db/schema.sql` is a parallel compatibility schema; `create table if not exists` does not reconcile its model assumptions with existing WP1 tables.
2. Move WP6 reads/writes off its duplicate model package and onto shared WP1 ORM entities/contracts. Keep WP6 service logic where it fits; replace the runtime path shim in `backend/app/wp6_integration.py` with explicit root-owned router/service composition after parity tests pass. Retire the WP6 schema init mount only after a clean-database migration and existing-database upgrade are proven.
3. Make WP4 publish transactionally create/update WP1 `job_offers` and `job_offer_skills`, not only set `EmployerDraftSession.draft.status = published`. Persist edits/review state and preserve employer ownership. Make profile, offer, match, application, and feedback writes use WP1 contracts.
4. Make authentication method independent from user type. Every candidate and employer must be able to register/sign in with either Google OAuth or email/password. Use one canonical `users` identity and separate linked authentication identities (for example, a provider-subject table for Google); normalize email and require verified email before account linking. Do not silently merge accounts: linking an existing Google identity and password account requires proof of both credentials. Replace the current single `users.role` assumption with additive role assignments so one account can hold candidate and employer roles; link both workspaces through `candidates.user_id` and `employers.user_id`. Migrate existing WP4/WP6 accounts without losing their profile/offer ownership.

### Phase 2: Secure Application Sessions and Data Access
1. Centralize token/session creation and verification in the root backend so both login methods issue the same short-lived, issuer/audience-validated session. Replace frontend `localStorage` bearer-token storage with a production session approach (recommended: Secure, HttpOnly, SameSite cookies) and add CSRF protection for state-changing requests.
2. Provide Google and email/password registration and login for both roles; role choice/workspace activation happens independently of identity provider. Require verified email for password accounts, include password reset and account recovery, rate-limit auth/OAuth/upload/AI endpoints, and support explicit Google/password identity linking with reauthentication.
3. Add role/ownership dependencies to private routes: candidates access only their profile/applications; employers access only their offers and policy-permitted applicant data. Allow a dual-role user to switch workspaces without creating a second identity. Complete consent versioning, export/deletion, CV/audio retention, PII-safe logging, audit events, and tested RLS or a documented least-privileged service boundary.

### Phase 3: End-to-End Candidate and Employer Product
1. Finish WP6 candidate profile editing using WP1 reference codes: skills and levels, work history, education, languages, target occupations, location, and availability. Preserve the existing CV parser and stateless assistant as draft helpers; require review and consent before save. Integrate WP2 guided/voice onboarding as the alternate path for people without a CV, returning the same canonical profile contract.
2. Integrate WP3 scoring behind the root API using canonical candidate/offer data and WP1 `RankedMatches`, `MatchResult`, and `Roadmap` contracts. Replace WP3’s local SQLite/demo offer boundary with shared Postgres reads/writes and persist versioned scores/gaps/roadmaps. Do not display fabricated dashboard counts or fit percentages.
3. Implement candidate offer discovery, match explanation, application create/withdraw/status, and roadmap views; implement employer offer list/edit/publish, applicant list, decision, and hiring feedback. Persist each operation to WP1 tables and enforce role/ownership checks.
4. Reuse WP4’s guided interview/review UI and WP6’s profile/onboarding components in the root frontend, removing duplicate or package-local browser API assumptions only after root equivalents are verified. Add guarded routes, a role-aware account/workspace switcher for dual-role users, provider-neutral login/signup screens (Google or email/password), identity-linking/recovery states, and loading/empty/error/retry states, validation, keyboard/mobile behavior, and French/Arabic direction support where those journeys expose Arabic content.

### Phase 4: Production Operations and Delivery
1. Add backend and frontend container builds and a production Compose/staging profile; keep PostgreSQL/pgvector as the canonical database. Add a one-shot, versioned migration runner instead of relying on Postgres container init scripts for upgrades. Keep development seeds opt-in and impossible to run in production.
2. Add CI for backend tests, frontend typecheck/build, WP1 SQL/ORM/schema sync, dependency/security scanning, and migration application against a clean PostgreSQL service. Resolve database-dependent tests that currently skip in the local environment; require zero skips for release-critical Postgres integration tests.
3. Add structured logs with request/correlation IDs, redaction rules, latency/error metrics, exception reporting, readiness checks for required services, and alerts/runbooks. Define TLS, secret management/rotation, encrypted backups, restore drills, migration rollback/forward-fix policy, and incident ownership. Select a cloud/host and pilot domain before the release-candidate phase.

### Phase 5: Release Gates
1. Run a clean-environment deployment rehearsal from a fresh database and an upgrade rehearsal from the current schema; verify migrations, seed policy, backup restore, OAuth redirect, and Postgres-only operation.
2. Run API integration tests across Google/employer auth, profile save, WP2 intake, WP3 ranking, WP4 offer publish, candidate application, employer decision/feedback, and persisted WP1 rows. Use real Postgres in CI; stub only external Google/Groq/LLM boundaries.
3. Run Playwright journeys at desktop and mobile sizes, including signed-out/expired session, candidate consent/profile, CV failure and retry, no matches, apply/withdraw, employer draft/review/publish, applicant decision, and service/database error states. Add accessibility checks for keyboard navigation, form labels/errors, contrast, and responsive text.
4. Approve pilot only when security/privacy review is complete, critical journeys pass, no fake data remains, no production secrets are in the repo/client bundle, database migrations/backups are demonstrated, and operational dashboards/alerts/runbooks are owned.

**Relevant files**
- `backend/app/main.py`, `backend/app/wp6_integration.py` — root composition; remove the dynamic WP6 import bridge after explicit shared-service composition is tested.
- `backend/app/config.py`, `backend/app/security.py`, `backend/app/google_auth.py` — settings, token/session lifecycle, Google auth, and employer auth.
- `backend/app/models.py`, `backend/app/database.py`, `backend/app/schemas.py` — current root ORM/DB boundary; reconcile employer/session entities with `data-layer-wp1/mahara_data/db/models/` and published contracts.
- `migrations/20260921000000_wp1_shared_schema.sql`, `migrations/20260922000000_employer_draft_sessions.sql`, `employee-module-wp6/db/schema.sql`, `compose.yaml` — canonical migration history and current WP6 compatibility initialization.
- `employer-agent-wp4/employer_agent_wp4/router.py`, `employer-agent-wp4/employer_agent_wp4/workflow.py` — existing offer draft/review/publish behavior; make publish persist the WP1 offer records.
- `employee-module-wp6/backend/app/services/profile.py`, `employee-module-wp6/backend/app/auth.py`, `employee-module-wp6/backend/app/models.py` — reuse business behavior while replacing copied persistence/auth wiring.
- `skill-matching-wp3/main.py`, `skill-matching-wp3/scoring.py`, `skill-matching-wp3/profile_store.py` — current matching API/scoring and SQLite boundary to adapt to WP1 contracts/PostgreSQL.
- `onboarding-agent-wp2/main.py`, `onboarding-agent-wp2/workflow.py`, `onboarding-agent-wp2/frontend/src/api.js` — existing guided intake and package-local API assumptions.
- `frontend/src/App.tsx`, `frontend/src/lib/api.ts`, `frontend/src/pages/CandidatePage.tsx`, `frontend/src/pages/EmployerPage.tsx`, `frontend/src/pages/DashboardPage.tsx` — canonical frontend shell and current integrated journeys.
- `backend/requirements.txt`, `backend/.env.example`, `frontend/package.json`, `README.md` — dependencies, configuration, runbooks and release instructions.
- Add `.github/workflows/ci.yml`, `backend/Dockerfile`, and frontend production-serving configuration if no existing deployment workflow is selected.

**Verification**
1. Run `python -m pytest -q` in `backend/`, WP6 unit tests, WP4 tests, WP1 contract/migration tests, and WP3 tests. Release-critical integration tests must run against PostgreSQL and may not silently skip.
2. Start a clean Postgres 16 + pgvector database; apply all versioned migrations; assert WP1 ORM/SQL parity, seeded reference data, and all required indexes/constraints. Repeat as an upgrade from the current schema.
3. Use API tests to exercise the complete authenticated candidate/employer loop and verify database rows/status transitions, cross-account denial, token expiry, consent, and no publication before review. Test Google and email/password signup/login for both candidate and employer roles, explicit identity linking, verified-email requirements, password recovery, and dual-role workspace switching.
4. Run `npm run build`, frontend unit/component checks, and Playwright desktop/mobile journeys against a deployed staging stack.
5. Verify backup restore, health/readiness behavior, metrics/log redaction, secret handling, and deployment rollback/forward-fix procedures in staging.

**Decisions**
- Target is a limited production pilot, not an unrestricted public launch.
- Launch-critical product boundary is candidate-to-employer matching and application, including employer offer creation/review/feedback.
- PostgreSQL + WP1 remain the only canonical data source; WP-specific code may remain as implementation modules but not as independent storage/auth/API silos.
- Every candidate and employer can use either Google or email/password; authentication method never determines authorization role.
- One account may hold both candidate and employer roles. Store Google identity links and password credentials against the same normalized, verified `users` account; link identities only after proof of both methods, never through silent email-only merges.
- Password email verification, reset/recovery, uniform token/session behavior, and workspace-scoped authorization are pilot release gates.
- The deployment provider is not yet chosen; keep early container/CI design portable and select a host before staging/release rehearsals.
- Excluded from initial pilot unless later prioritized: WP5 ministry/admin dashboards and large-scale multi-tenant/SLA claims. Keep the schema/security extension points but do not delay the core candidate-employer loop for them.

**Further Considerations**
1. Confirm preferred cloud/host before Phase 4 staging work; until then, keep the plan vendor-neutral.
2. Confirm pilot country/privacy counsel and retention periods for CVs, voice transcripts, and profile data before accepting real users.