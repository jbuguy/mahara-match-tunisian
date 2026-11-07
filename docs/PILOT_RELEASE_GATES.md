# Pilot release gates

This checklist tracks the release gates from the production-pilot plan. A
passing CI run is necessary, but it does not approve a production pilot.

## Started in Phase 5

- [x] Separate API process liveness (`/health/live`) from database readiness
  (`/health/ready`). Readiness runs a query against the configured database and
  returns a generic 503 when that required service is unavailable.
- [x] Add CI jobs for the current backend suite, frontend tests/build, a clean
  PostgreSQL migration, and an upgrade from revision
  `0019_missions_and_proposals` to the current migration head.
- [ ] Confirm CI passes on the repository host. This checkout has no configured
  Git remote, so a hosted run cannot be observed here.

## Pilot gates still open

- [ ] Fresh deployment and upgrade rehearsals against the actual selected
  staging configuration, including encrypted backup and restore.
- [ ] PostgreSQL-backed critical journey coverage. Current API tests construct
  an in-memory SQLite schema; the new PostgreSQL job checks migration behavior
  but does not yet run the application journey against PostgreSQL.
- [ ] Google OAuth, verified email, identity linking/recovery, dual-role
  workspace authorization, and their redirect journeys. These are not present
  in the current root application, so the plan's Google and dual-role journeys
  cannot pass yet.
- [ ] Desktop and mobile Playwright journeys and accessibility checks. The
  repository currently has component tests but no Playwright setup.
- [ ] Security/privacy review, production-secret and fake-data review,
  operational alert/runbook ownership, and an approved pilot host/domain.

## Local verification commands

Run from the repository root after installing the documented dependencies:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest -q backend/tests
npm test
npm run build
```

The PostgreSQL migration rehearsals run in `.github/workflows/ci.yml`. Do not
run demo seed commands in production; the seed command rejects the production
environment and requires explicit local opt-in.
