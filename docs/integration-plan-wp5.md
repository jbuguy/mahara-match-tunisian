# WP5 Integration Plan: Admin & Ministry

## Goal

Integrate Workpackage 5 (WP5) into the single platform runtime so ministry administrators can govern the national skills and occupation referentials, review incoming suggestions, ingest labour-market datasets, inspect ingestion outcomes, view privacy-safe analytics, and monitor platform quality. WP5 must use the root FastAPI application, WP1's canonical PostgreSQL schema hosted by Supabase, and the platform's authentication and audit rules.

The implementation should leave WP5 with clear HTTP/router, service, repository, schema/contract, and frontend boundaries. Any schema change must be an ordered root migration. Existing WP1 models, tables, and contracts remain canonical.

## Repository baseline

- `admin-ministry-wp5/backend/app/main.py` is a standalone FastAPI app. Its routers cover taxonomy, occupations, suggestions, market datasets, ingestion jobs, analytics, monitoring, and health. The root app does not currently mount WP5.
- WP5's `backend/app/db.py` creates its own SQLAlchemy engine from WP5 settings. WP5 services query WP1 `mahara_data` models, and WP1's root migration already defines the skills, occupations, suggestions, market datasets/indicators, ingestion jobs, and audit-log tables WP5 needs.
- The root backend already owns Supabase PostgreSQL configuration, migrations, shared authentication/runtime, and examples of repository/service/router layering (notably offers and applications). It should own WP5's DB sessions and engine after integration.
- `admin-ministry-wp5/frontend` is an independent Vite app. Its current `App.tsx` only renders `SkillsPage`; other backend workflows have no corresponding screens. The platform frontend currently has candidate/employer flows and no ministry area.
- WP5 currently has service modules, but most contain both business rules and direct SQLAlchemy queries. There is no dedicated repository layer. Its admin endpoints also need platform role enforcement before they are exposed through the root API.
- WP5 has a local in-memory request metrics collector. That is useful for development but is not durable or multi-worker production telemetry.

## Integration progress

The first integration slice is in progress. The root API now mounts WP5 taxonomy, suggestion, occupation, market, ingestion, analytics, and monitoring routers under `/api/v1/admin`. Those routes use the root Supabase-backed SQLAlchemy session and require the `ministry_admin` user role. Governance writes that already produced audit events now attach the acting user, and market submissions set `uploaded_by`. The platform frontend has a role-aware ministry entry and a tabbed workspace for the existing WP5 list/report endpoints, with skill validation available from the skills table.

The standalone WP5 app has not yet been retired, the remaining service-to-repository extraction is still pending, and the ministry UI does not yet expose all create/edit/review/upload actions. Production telemetry is still process-local. Continue with the remaining sequence below before treating WP5 as release-ready.

## Integration principles

1. Root `backend` is the only API runtime, and root `migrations/` is the only migration sequence.
2. Supabase is the PostgreSQL host. The backend connects using the root `DATABASE_URL` with SSL; credentials and any Supabase service-role key remain server-side. The browser uses authenticated root API endpoints only.
3. WP1 owns canonical models, enums, contracts, and table definitions. WP5 owns governance and ministry workflow behavior.
4. Routers handle HTTP concerns; services enforce workflow and authorization rules; repositories own persistence queries and mutations; WP1 models/contracts remain the source of shared data shape.
5. Every write that changes governed data or review decisions records an authenticated actor and useful audit metadata.
6. Ministry analytics expose aggregate data only and preserve the existing k-anonymity threshold. Never expose candidate-level records through WP5.
7. All WP5 endpoints require an authenticated ministry/admin role. UI hiding is not authorization.

## Target structure

Keep the existing WP5 module package during integration, but mount it from the root backend and remove its duplicate runtime/database setup. A target structure could be:

```text
backend/app/
  wp5/
    routers/       # HTTP adapters; request parsing, auth dependency, response mapping
    services/      # governance, ingestion, analytics, monitoring workflows
    repositories/  # WP1 model queries and persistence
    schemas.py     # WP5-specific request/response schemas where WP1 has no contract
```

Alternatively, preserve `admin-ministry-wp5/backend/app` as an importable package and place repositories/services there; do not keep two independently configured FastAPI/DB runtimes. Choose one layout during phase 1 and document it. Prefer no copies of WP1 entities or schema definitions.

## Work sequence

### 1. Audit contracts, ownership, and authorization

- Map each WP5 route and operation to its WP1 model/table and contract: skills, occupations/required skills, skill suggestions, market datasets/indicators, ingestion jobs, audit logs, and aggregate skill gaps.
- Confirm the ministry/admin role claim and principal dependency in the root auth implementation. Define which roles can read, create/edit, validate/retire, approve/merge/reject, ingest datasets, view analytics, and inspect audit/monitoring data.
- Define audit fields for all governance decisions and market imports: actor user ID, action, entity, entity ID, timestamp, and non-sensitive change context. Do not put raw candidate data or secrets in audit payloads.
- Confirm API paths and response shapes to preserve where practical, and define versioning/deprecation for any required changes.
- Check whether there is existing WP5-only data outside the root Supabase schema. If so, document a data-preserving migration/import before removing the standalone DB configuration.

**Exit:** a reviewed route-to-role-to-data matrix and confirmed canonical data source.

### 2. Integrate the backend runtime and persistence

- Mount WP5 routers in `backend/app/main.py` under the platform API prefix and a clear admin/ministry namespace. Reuse root DB session dependency, engine, configuration, CORS, error handling, and auth dependencies.
- Remove WP5 engine/session creation and standalone app startup from the integrated path. Keep only compatibility wrappers if tests or local package tooling require them, and ensure they delegate to root configuration.
- Extract query and write code from each WP5 service into repositories using WP1 SQLAlchemy models. Keep lifecycle rules, validation, orchestration, and contract mapping in services. Keep routers thin and convert domain errors through root error conventions.
- Reconcile transaction handling: each create/update/validate/approve/merge/reject/ingest operation should commit atomically, roll back on failure, and avoid partially recorded dataset/job state.
- Ensure taxonomy search and list endpoints paginate with bounded page sizes and deterministic ordering; add indexes only through a new root migration when query evidence warrants them.
- Move audit writes to a shared audit repository/service (or an explicitly agreed WP5 adapter) so actor identity is available and audit semantics match the rest of the platform.
- Treat the current in-memory metrics as development-only. Integrate production metrics/logging/tracing with the platform observability stack, and avoid exposing sensitive route labels or unbounded cardinality.
- Review database access against Supabase connection pooling. Use a supported direct/session-pooler URL for migration execution; use a suitable pooled connection for runtime only after validating SQLAlchemy and transaction behavior. Keep DB credentials out of logs and responses.

**Exit:** root FastAPI serves WP5 endpoints through the shared Supabase-backed session, with repository/service/router separation and authenticated audit context.

### 3. Close production security and data-quality gaps

- Enforce ministry/admin roles on every WP5 route, including monitoring and audit routes. Test both missing authentication and authenticated non-admin access.
- Confirm Supabase RLS policies and DB roles are intentional. The root migration currently enables RLS as defense-in-depth and notes that application authorization is enforced by APIs; verify the runtime database role and policies rather than assuming RLS protects an overly privileged connection.
- Validate all codes and foreign keys against canonical WP1 rows. Keep taxonomy transitions explicit and reject invalid lifecycle changes consistently.
- Add request size limits and safe validation for market dataset submissions (the request currently accepts up to 5,000 records), including duplicate/idempotency behavior, row-level rejection reporting, and safe retry semantics.
- Review analytics aggregation for k-anonymity correctness across every grouping and filter combination; ensure suppressed counts cannot be inferred by repeated queries or narrow filters.
- Add timeouts and bounded result sizes to monitoring/analytics queries. Health endpoints should distinguish liveness from Supabase readiness without leaking connection details.
- Ensure errors, logs, exports, and audit records do not include credentials, raw candidate data, or uploaded sensitive content.

**Exit:** authorization, privacy, input bounds, failure handling, and Supabase access assumptions are explicit and covered by integration checks.

### 4. Integrate and complete the ministry frontend

- Decide whether the ministry area is mounted in the root frontend shell or remains a separately built frontend deployed against the root API. Prefer a shared shell when it can reuse platform login, role-aware navigation, API client, and design system without destabilizing candidate/employer routes.
- Configure one API base URL per environment, pointing to the root API. Remove the WP5 standalone port default from production configuration. Use the platform auth/session mechanism and never store Supabase credentials in Vite variables.
- Keep and improve the current skills list, search, pagination, and validation flow. Add creation/edit/detail and retire/deprecate confirmation where supported by the API.
- Add an occupations and required-skills screen with search, create/edit, lifecycle actions, and skill requirement editing.
- Add a suggestion-review inbox with approve, merge-to-existing-skill, and reject actions, including duplicate/conflict feedback and decision confirmation.
- Add market dataset upload/submission and dataset detail screens with period/origin metadata, record counts, rejection details, and retry guidance.
- Add ingestion jobs history/detail screens with status, pipeline version, row totals, errors, and timestamps.
- Add a ministry analytics screen for skill-gap maps with date range and supported filters, visible k-anonymity/suppression messaging, and accessible tabular alternative to any map/chart.
- Add monitoring overview, taxonomy quality, and audit-trail screens only for authorized users. Show operational errors in a user-safe manner and provide loading, empty, permission-denied, and retry states.
- Keep French and Arabic/Derja fields usable, right-to-left text readable, and screens keyboard accessible and responsive.

**Exit:** an authorized ministry user can complete governance and data-review workflows from the UI without a separate WP5 login or database connection.

### 5. Supabase schema and deployment readiness

- Compare WP5 model usage with the existing root migration and WP1 ORM metadata. Do not replay WP5 schema creation or apply a parallel SQL schema.
- Create a new ordered root migration only for a confirmed missing schema requirement, with backward-compatible rollout and rollback/data-recovery notes.
- Verify grants/RLS for the backend runtime role, migration role, and any read-only analytics role. The browser must not receive a privileged Supabase key.
- Add WP5 router/service/repository modules to root CI and deployment packaging. Remove obsolete standalone deployment/env instructions or mark them clearly as development-only.
- Document Supabase project setup, SSL URL configuration, migration order, required auth roles, secrets, operational alerts, backups, and data retention.

**Exit:** a clean Supabase database migrates once through the root sequence and the deployed root API has the least required permissions and runtime configuration.

### 6. Verify the integrated workflows

- Migration/model checks: clean Supabase project, ordered root migration, ORM/schema parity for touched objects, and no duplicate WP5 schema application.
- Repository/service checks: taxonomy lifecycle, occupation skill replacement, suggestion outcomes, ingestion transaction rollback/retry, aggregate suppression, and audit actor attribution.
- API integration checks: role matrix, invalid transitions, missing/duplicate codes, missing taxonomy references, payload boundary, stable pagination, and sanitized errors.
- Privacy checks: no candidate-level data in ministry responses; k-anonymity holds under filters; audit payloads exclude PII/secrets; unauthorized roles cannot read audit or admin data.
- Frontend checks: each workflow's success, empty, loading, validation, conflict, permission, network-failure, and retry states; responsive and RTL behavior.
- Operational checks: Supabase unavailable/slow behavior, liveness/readiness, connection pool exhaustion handling, log/metric cardinality, and secret redaction.

**Exit:** root and UI checks pass against the shared runtime and a clean migrated Supabase project; the deployment and operator docs reflect the integrated architecture.

## Suggested milestones

| Milestone | Deliverable | Depends on |
|---|---|---|
| M1: Contract and access model | Route/data/role matrix, data-source audit, API compatibility decisions | — |
| M2: Shared backend integration | Root-mounted routers, root Supabase session, repositories and services | M1 |
| M3: Secure production behavior | Role checks, actor-aware audit, bounded ingestion/analytics, observability | M2 |
| M4: Ministry UI | Connected governance, review, ingestion, analytics, audit and monitoring screens | M2, M3 API contracts |
| M5: Release validation | Supabase migration/access validation, workflow checks, deployment docs | M3, M4 |

## Decisions to record during phase 1

- Whether WP5 UI joins the root frontend or remains a separately deployed Vite bundle using the root API.
- Exact role names and whether ministry users can validate referentials or only propose changes for a separate reviewer.
- Whether dataset ingestion is synchronous at the current 5,000-record limit or should enqueue durable background jobs.
- Required market data formats, maximum upload/request sizes, and whether idempotency keys are needed for safe retries.
- Production observability provider and retention for request metrics and governance audit history.
- Supabase runtime and migration DB roles, connection modes, and applicable RLS policies.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| WP5 admin endpoints are mounted without role checks | Make role dependencies mandatory at router boundaries and cover every route with authorization checks. |
| A separate WP5 DB configuration drifts from Supabase/root migrations | Remove the integrated engine path and use the root DB dependency and migration sequence only. |
| RLS is assumed to protect data despite a privileged runtime connection | Inspect actual Supabase grants/policies and test with the deployed DB role; keep API authorization authoritative. |
| In-memory metrics disappear across restarts and workers | Replace them with platform metrics/telemetry before relying on them for production alerts. |
| Ingestion fails midway or duplicate retries create inconsistent datasets | Use atomic transactions, explicit job states, idempotency strategy, and row-level rejection reporting. |
| Analytics leaks small groups through filters | Apply and test k-anonymity after all query filters, suppress results consistently, and constrain query dimensions. |
| Missing ministry screens leave API features unreachable | Treat each backend workflow's UI screen and empty/error states as a milestone exit condition. |
