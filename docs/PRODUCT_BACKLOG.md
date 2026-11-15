# Mahara Match Product Backlog

## Product purpose

Mahara Match is a Tunisia-focused skills-to-opportunities platform. It helps
candidates build a skills profile and prepare for work; employers publish jobs
and manage recruitment; training providers publish courses; and individuals
and organizations publish independent missions or professional services.
Ministry users get an observatory of platform activity alongside carefully
labelled public labour-market context.

The product combines user- and organization-entered platform records with a
reviewed public-data collection and retrieval pipeline. It is not a national
vacancy registry: job offers are employer supplied, match scores explain skill
evidence rather than predict hiring, and ministry platform metrics do not
represent the whole Tunisian labour market.

## What this backlog represents

I reviewed the current README, product and data documentation, task tracker,
frontend navigation/workspaces, backend routes/models, tests, and Git history
through commit `457e57c`. The repository records work packages, pull requests,
commits, and outstanding validation tasks, but it does not establish a
verified two-sprint calendar or named historical team assignments.

The history includes work-package commits for onboarding, skill matching,
employer features, ministry administration, and later integration and
marketplace work. It does not label two formal sprint boundaries.

The two sprint backlogs below are therefore grounded in functionality and
evidence that exist in this repository, with current implementation status
shown. They are credible reconstructed delivery backlogs, not claims that all
the work was originally completed in exactly two timeboxed sprints. The later
prioritized backlog covers remaining improvements.

## Current product baseline

The repository includes candidate profiles, CV-assisted suggestions, skill
catalogue and relationship-based matching, published-offer applications,
career roadmaps, interview preparation, role-based assistants, employer
recruitment and workforce planning, provider courses and enrollments,
professional profiles/services, missions and proposals, aggregate ministry
analytics, and operator audit events. It also includes reviewed public
labour-market data, Tunisian administrative location references, and platform
activity data. The sprint backlogs group these actual product areas and note
what still needs validation.

The November 7 audit is a dated snapshot and predates later implementation;
where it conflicts with current routes or tests, the backlog follows the
current code. Open checks remain in `TASKS.md` and `docs/PILOT_RELEASE_GATES.md`.
External data, platform activity, synthetic demo data, and employer-reported
outcomes must remain clearly distinguishable.

## Five-person team organized by product area

The repository does not document a verified historical roster. For planning
and presentation, this is the five-area team structure requested:

The five people cover the five product areas, with one person responsible for
each area. Onboarding Agent and Voice is a single person's area.

| Person | Product area | Implementation responsibility |
| --- | --- | --- |
| 1 | Onboarding Agent and Voice | Candidate onboarding, CV/profile assistant, voice input/transcription, saved assistant sessions, and manual fallbacks. |
| 2 | Employer | Organization and offer management, recruitment lifecycle, candidate discovery, and employer workforce planning. |
| 3 | Candidate | Candidate opportunity/application journey, career roadmap, interview preparation, courses, and service requests. |
| 4 | Ministry | Reviewed labour-market data intake, location references, observatory indicators, provenance, and privacy controls. |
| 5 | Skill Matching | Skill catalogue/relationships, explainable matching, skill gaps, roadmap inputs, and training alignment. |

Responsibilities can overlap when discussing a small team. The whole team
shares refinement, review, testing, and delivery; these responsibilities are
part of each product area's work. In this example, every person has a concrete
implementation contribution in one named product area.

## Repository-grounded two-sprint backlogs

The backlog items below are based on implemented screens, API routes, data
models, tests, task status, and commit history. “Current status” describes the
repository at the reviewed revision; it is not a claim that every feature is
production-ready. Since the repository has no confirmed sprint calendar, these
are source-grounded sprint backlogs, not a retrospective asserting that these
exact stories were delivered in two historical timeboxes.

### Sprint 1 — Build the skills-to-opportunities foundation

**Sprint goal:** Establish the shared access and data foundations, then give a
candidate a practical path from profile creation to relevant, published
opportunities.

| ID | Delivered backlog item | Area | Current status and repository evidence |
| --- | --- | --- |
| S1-01 | Shared authentication, candidate registration, JWT sessions, five role workspaces, organization membership/ownership checks, and privacy-conscious audit events. | Shared / Employer | Implemented. `backend/app/main.py`, `backend/app/permissions.py`, `backend/app/models.py`, `backend/tests/test_auth_access.py`, `src/App.tsx`. |
| S1-02 | Candidate onboarding and editable profile; CV parsing provides suggestions for review before saving, with a manual editing path and Tunisian governorate/municipality selection. | Onboarding Agent and Voice | Implemented. `backend/app/cv_parser.py`, `backend/tests/test_candidate_onboarding.py`, `src/workspaces.tsx`, `src/components/ProfileBuilder.tsx`, `src/components/LocationSelect.tsx`. |
| S1-03 | Candidate career assistant with Derja/Arabic/French interaction, saved owner-scoped sessions, optional speech transcription/synthesis, and explicit unavailable-service behavior. | Onboarding Agent and Voice | Implemented; final session and desktop/mobile navigation regression checks remain open. `backend/app/assistant_rag.py`, `backend/app/assistant_services.py`, `backend/tests/test_assistant_sessions.py`, `src/workspaces.tsx`. |
| S1-04 | Curated skill catalogue and aliases; direct, related, and foundational skill evidence produces an explainable match score; skill gaps feed a candidate roadmap. | Skill Matching | Implemented. Scores are deterministic evidence summaries, not hiring predictions; related/foundational edges receive partial credit. `backend/app/matching/scoring.py`, `backend/app/skill_catalog.py`, `backend/tests/test_matching_scoring.py`, `backend/tests/test_skill_relationship_migration.py`, `backend/tests/test_career_roadmap.py`. |
| S1-05 | Employer organization/profile and job-offer authoring; draft/publish/pause lifecycle; candidates discover and apply to published offers and track application status. | Employer / Candidate | Implemented. Applications against unpublished offers are blocked. `backend/app/marketplace.py`, `backend/tests/test_matching_offers.py`, `backend/tests/test_marketplace.py`, `src/workspaces.tsx`, `src/GuestDiscovery.tsx`. |
| S1-06 | Reviewed public-data collection, normalization, snapshot/checksum recording, and ingestion into searchable knowledge documents/chunks for multilingual retrieval. | Ministry | Implemented for configured sources; it is not a live Tunisian vacancy feed. `backend/app/data_pipeline.py`, `backend/app/ingest_labour_data.py`, `backend/app/knowledge_base.py`, `backend/tests/test_data_pipeline.py`, `backend/tests/test_assistant_rag.py`. |
| S1-07 | French-first shared application shell, role-specific navigation, reusable UI components, theme selection, and Arabic right-to-left support. | Shared / all areas | Implemented. `src/App.tsx`, `src/i18n.ts`, `src/components/`, `src/App.test.tsx`. |

**Sprint 1 data actually collected or processed**

- **Candidate-provided:** profile details, declared skills, education,
  experience, and location. CV extraction is a suggestion flow; the candidate
  reviews changes before saving.
- **Employer-provided:** organization profile and job-offer details, required
  skills, and offer lifecycle state. Only published offers enter candidate
  discovery and matching.
- **Platform workflow:** applications and their status history, scoped to the
  candidate and authorized employer.
- **Public sources:** World Bank Tunisia unemployment, youth unemployment,
  and employment-to-population indicators; Tunisia open-data vocational
  specialities (2017) and agricultural-investment job counts; Eurostat
  France unemployment and France Travail BMO source/catalogue data for
  comparison context.
- **Location reference:** static governorate and municipality-area snapshots
  based on INS Tunisia administrative data distributed through HDX; loaded
  from committed data, not fetched at runtime.
- **Demo-only:** synthetic offers and ministry indicators are labelled as
  synthetic and are not market evidence.

**Sprint 1 demo outcome:** Sign in to role-specific workspaces; create and
review a candidate profile; publish an employer offer; inspect the skill
match explanation, apply, view the roadmap, and trace a public indicator to
its source.

### Sprint 2 — Complete the multi-sided marketplace and observatory

**Sprint goal:** Extend the foundation into full recruitment, career
preparation, training, professional-service and mission workflows, and
privacy-preserving labour-market monitoring.

| ID | Delivered backlog item | Area | Current status and repository evidence |
| --- | --- | --- |
| S2-01 | Employer recruitment lifecycle: consent-aware candidate discovery, saved talent pools, application details/notes/evaluations/status history, messaging, interviews, offer decisions, notifications, organization verification, and employer analytics. | Employer | Implemented. `backend/app/employer.py`, `backend/tests/test_employer_workflows.py`, `src/marketplace.tsx`. Hires are employer-reported. |
| S2-02 | Organization-scoped workforce-planning sessions with messages, selected context/documents, structured analysis and recommendations, employer review, and draft offers generated only from approved recommendations. | Employer | Routes and persistence exist; end-to-end acceptance and regression checks remain open. `backend/app/planning.py`, `backend/tests/test_employer_planning.py`, `src/EmployerPlanningWorkspace.tsx`, `TASKS.md`. |
| S2-03 | Candidate technical/behavioral assessments and mock interview preparation, reviewable transcript capture, coaching/progress reports, and course recommendations for missing role skills. | Candidate / Skill Matching | Implemented; final phase 7/8 integration and phase 10 regression checks remain open. Text answers are not executed and raw audio is not retained. `backend/app/technical_assessment.py`, `backend/app/behavioral_assessment.py`, `backend/app/interview_transcription.py`, related `backend/tests/test_*assessment.py` and `test_interview_prep.py`, `src/workspaces.tsx`. |
| S2-04 | Training-provider course create/edit/publish/archive; public course discovery; candidate enrollment; provider roster and completion/withdrawal management. | Candidate / Skill Matching | Implemented. Provider dashboard and catalogue navigation currently share a screen, so the UX is not fully separated. `backend/app/marketplace.py`, `backend/tests/test_marketplace.py`, `src/marketplace.tsx`, `src/App.tsx`. |
| S2-05 | Public professional profiles and service listings; service requests with accept/decline, agreed scope, progress, completion confirmation, dispute, and eligible review; independent missions with proposals and status history. | Employer / Candidate | Implemented as flows separate from job applications. `backend/app/professional.py`, `backend/app/service_requests.py`, `backend/app/missions.py`, `backend/tests/test_marketplace.py`, `src/ProfessionalServices.tsx`, `src/ServiceRequestsWorkspace.tsx`, `src/MissionsWorkspace.tsx`. |
| S2-06 | Ministry observatory: platform KPIs, recruitment funnel/time-to-hire, governorate and youth breakdowns, skills gap, training alignment, employer-quality indicators, national context, and logged exports. | Ministry / Skill Matching | Implemented in API and UI with metadata and suppression helpers; privacy review is still needed across every derived metric (including zero-sized cohorts), export, and chart before policy-facing use. `backend/app/marketplace.py`, `backend/app/analytics.py`, `backend/tests/test_admin_analytics.py`, `src/components/AdminObservatoryDashboard.tsx`. |
| S2-07 | Unified assistant workspace for authenticated roles, persistent searchable conversations, floating entry point, employer project context, browser voice input, and read-aloud. | Onboarding Agent and Voice | Implemented; full desktop/mobile navigation verification remains open. `src/UnifiedAssistantWorkspace.tsx`, `src/components/FloatingAssistant.tsx`, `src/App.tsx`, `backend/tests/test_assistant_sessions.py`. |
| S2-08 | Operational and release foundations: append-only audit viewing, separate process liveness/database readiness, CI for backend/frontend and migration checks, and role-aware responsive screens. | Ministry / all areas | Partially implemented. Operator audit and health endpoints exist; the operator “Services” screen is still a placeholder. PostgreSQL application journeys, staging backup/restore, hosted CI confirmation, and Playwright/accessibility release checks remain open. `backend/app/audit.py`, `backend/app/main.py`, `backend/tests/test_health.py`, `docs/PILOT_RELEASE_GATES.md`, `src/App.tsx`. |

**Sprint 2 data actually collected or processed**

- Recruitment events: employer-reviewed applications, status changes,
  interviews, messages, decisions, notifications, and declared outcomes.
- Training records: provider-authored course details, candidate enrollments,
  and enrollment states; these are not proof of independently verified
  employment outcomes.
- Career preparation: assessment answers and results, with audio used for
  transcription but not retained as raw audio.
- Marketplace records: public professional profiles/listings, private
  proposals, participant-scoped service requests, completion, disputes, and
  reviews.
- Observatory inputs: platform activity and sourced external series. Ministry
  APIs are intended to return aggregates only, never individual candidate
  records. The privacy rule requires groups under five to be `null` with
  `suppressed: true`; the current zero-person case is a known implementation
  gap.

**Data presentation and privacy rules**

- Count published offers and courses; exclude drafts, closed offers, and
  duplicate offers unless an explicit report requirement says otherwise.
- Label World Bank unemployment values as modelled ILO estimates; agricultural
  job counts as investment-project-attributed jobs, not vacancies; and the
  2017 vocational list as historical, not current course availability.
- Label hires as employer-declared and distinguish platform metrics from
  external series/units. France remains comparison context only.
- Metric/chart responses and exports must retain `source`, `source_url`,
  `period`, `methodology`, and `retrieved_at`.
- Never expose candidate-level ministry data. Do not rely on UI-only
  suppression for small cohorts.

**Sprint 2 demo outcome:** Walk through the five roles and the public
professional/mission paths; demonstrate recruitment, planning, interview
preparation, course enrollment, service lifecycle, and observatory filters,
exports, provenance, and suppression. Explicitly show the operator Services
placeholder as an outstanding limitation, not an available feature.

## Open work confirmed by the repository

These are real follow-up items, not invented product features:

- **Assistant:** complete owner/session/migration regression checks and verify
  desktop/mobile navigation after the final session guard changes.
- **Interview preparation:** finish end-to-end integration checks for CV
  evidence and course recommendations, then run the full workflow regressions.
- **Employer planning:** verify organization isolation, document-source
  attribution, recommendation review, safe retries, and approved-recommendation
  draft creation end to end; publishing must remain an explicit employer act.
- **Observatory:** audit every endpoint, filter, export, and chart for source
  metadata and disclosure control. The current `suppress_small` helper
  suppresses counts 1–4 but returns zero unsuppressed, so test and resolve the
  known zero-person gap and derived small-cohort ratios before policy-facing
  use.
- **Provider/operator UX:** separate or consolidate the provider dashboard and
  catalogue destination; replace or remove the operator Services placeholder.
- **Pilot readiness:** run application journeys against PostgreSQL; rehearse
  staging deployment, upgrade, encrypted backup, and restore; confirm hosted
  CI; add desktop/mobile browser and accessibility checks; review identity,
  privacy/security, synthetic data, runbooks, alerts, and pilot hosting.

The tracker and release-gate document remain the source of truth for completion
state; do not mark these items done based solely on a successful unit-test run.

## Prioritization and sizing

- **P0 — Release confidence:** close known checks and establish safe, verified
  core journeys before relying on the product with pilot users.
- **P1 — Product value:** improve role workflows and trustworthy observatory
  value after the foundations are stable.
- **P2 — Follow-on:** useful operational or quality improvements that can be
  prioritized after core pilot needs.
- **Story points** use a relative Fibonacci scale. Estimates are initial
  discussion aids, not commitments or hours. Re-estimate after refinement.
- **Status** describes the backlog item, not the pre-existing features it
  validates: all items below are proposed and not assigned to a sprint.

## Prioritized backlog

### P0 — Release confidence

#### PB-01 — Close pending assistant and interview-preparation checks

**User story:** As a candidate, I want my assistant conversations and
interview-preparation progress to work reliably so I can resume practice
without losing trust in the platform.

**Acceptance criteria**

- Assistant sessions can be created, reopened, renamed, and deleted by their
  owner; cross-user access is rejected.
- Assistant provider failures and invalid responses produce an honest,
  usable fallback and never imply that an unavailable service succeeded.
- Interview-preparation course recommendations and CV evidence are covered by
  focused regression tests.
- Raw audio and private conversation content are not written to audit details.

**Estimate:** 5 points

#### PB-02 — Verify the candidate opportunity-to-application journey

**User story:** As a candidate, I want to understand why a published offer
matches my profile and complete an application so I can choose a clear next
step.

**Acceptance criteria**

- A candidate can update their profile, see matches for published offers,
  distinguish direct from related/foundational skill evidence, apply, and see
  application status.
- Draft, paused, closed, and otherwise unpublished offers cannot be applied to.
- Empty, loading, validation, and API error states are understandable in
  French.
- Match explanations state that the score reflects skill evidence, not a
  prediction of hiring success.

**Estimate:** 5 points

#### PB-03 — Verify critical journeys against PostgreSQL

**User story:** As a pilot user, I want the existing employer and provider
workflows verified against the production database engine so their persisted
records and access boundaries behave as expected.

**Acceptance criteria**

- PostgreSQL-backed journeys exercise offer publication, candidate
  application/review, course publication, enrollment, and provider roster.
- Cross-organisation access and invalid state transitions are rejected by the
  API, not merely hidden in the UI.
- Existing SQLite tests remain useful for fast coverage, but do not stand in
  for PostgreSQL journey tests.
- Migration upgrade and clean-install CI jobs continue to pass.

**Estimate:** 8 points. Employer/provider behavior exists; this item closes a
database integration and release-confidence gap.

#### PB-04 — Verify observatory privacy and provenance end to end

**User story:** As a ministry user, I want the existing observatory's
aggregates, charts, and exports to preserve privacy and source meaning so I
can interpret them without seeing candidate-level records.

**Acceptance criteria**

- Ministry responses and exports expose aggregates only, with no candidate
  records or direct identifiers.
- Every server-side result based on fewer than five people, including zero and
  derived ratios, returns `null` with `suppressed: true`; add boundary tests
  for 0, 1, 4, and 5.
- Every metric/series response includes `source`, `source_url`, `period`,
  `methodology`, and `retrieved_at`; exports preserve those fields and the
  active filters.
- Only published offers and courses are counted; closed/duplicate offers are
  excluded unless a report explicitly documents another rule.
- Employer-declared hires remain labelled as reported; external indicators
  remain distinct from platform metrics and use separate axes when units
  differ.

**Estimate:** 8 points

#### PB-05 — Complete pilot deployment and release gates

**User story:** As a pilot operator, I want deployment, recovery, and critical
journeys rehearsed so the pilot can be launched with known operational risks.

**Acceptance criteria**

- Critical API journeys run against PostgreSQL, in addition to migration
  checks.
- Fresh deployment, upgrade, encrypted backup, and restore are rehearsed
  against the selected staging configuration.
- Desktop and mobile critical journeys are exercised, with accessibility
  checks recorded.
- Production secrets, synthetic data, privacy/security review, alerting and
  runbook ownership, and pilot host/domain are reviewed before approval.
- Hosted CI results are recorded; a passing CI run alone is not treated as
  pilot approval.

**Estimate:** 13 points

### P1 — Improve role-specific product value

#### PB-06 — Separate provider course management from provider reporting

**User story:** As a training provider, I want separate catalogue and dashboard
tasks so I can manage courses and understand enrollment activity without
confusing the two.

**Acceptance criteria**

- Provider navigation leads to distinct course-management and reporting
  destinations, or is consolidated into one clearly named destination.
- A provider can identify draft, published, and archived courses and reach
  the relevant course action.
- Course and enrollment information remains limited to the owning provider.
- Empty and error states explain the next available action in French.

**Estimate:** 5 points

#### PB-07 — Finish source-aware observatory presentation

**User story:** As a ministry user, I want the existing observatory to make
the limits and provenance of each series clear so I do not mistake platform
activity or historical indicators for national vacancy coverage.

**Acceptance criteria**

- Platform activity and external indicators are separate series and axes
  where their sources or units differ.
- World Bank unemployment figures are labelled as modelled ILO estimates.
- Agricultural job figures are described as project-attributed jobs, not
  vacancies; 2017 vocational specialities are labelled as historical
  taxonomy, not current courses.
- France observations are presented only as comparison context.
- Filters, visualizations, and exports preserve server-side suppression and
  source metadata, period, methodology, and retrieval time.
- Dashboard language is French and does not imply that platform offers
  represent all Tunisian vacancies.

**Estimate:** 5 points. Observatory endpoints and screens already exist; this
is a correctness and presentation pass, not a new dashboard build.

#### PB-08 — Align ministry administration claims with implemented scope

**User story:** As a ministry administrator, I want the product's advertised
administration features to match the available workflows so I can tell what is
supported and what is planned.

**Acceptance criteria**

- Document the implemented observatory, organisation verification, and
  logged-export workflows accurately.
- Do not imply that permission constants alone provide a referential editor,
  general ministry dataset-upload screen, or review queue; these are not
  established by the current route inventory.
- Decide whether those additional workflows are pilot requirements; if so,
  refine them as separate stories with permission, audit, provenance, and
  tests.
- Neither path exposes candidate-level ministry data.

**Estimate:** 3 points for scope/documentation; any additional admin workflow
requires separate refinement and estimation.

#### PB-09 — Improve account and organisation access lifecycle

**User story:** As a pilot participant, I want a dependable way to access and
recover my account and join the correct organisation so I can use my assigned
workspace safely.

**Acceptance criteria**

- The product owner selects the pilot identity requirements, including
  verified email, recovery, organisation onboarding, and whether dual-role
  accounts are supported.
- Implemented identity flows validate redirect and account-linking behavior
  and cannot grant unintended roles or organisation membership.
- Server-side authorization tests cover the chosen role and membership rules.
- Unsupported identity options are not presented as available features.

**Estimate:** 13 points after scope decision

#### PB-10 — Make operator service navigation actionable

**User story:** As an operator, I want the service area to show safe, useful
operational status so I can understand availability without access to secrets
or candidate data.

**Acceptance criteria**

- The product owner chooses to implement a bounded status view or remove/
  rename the unsupported navigation destination.
- Any implemented status distinguishes process liveness from dependency and
  database readiness.
- The view exposes no credentials, personal records, or configuration
  secrets.
- Access is role-checked server-side and covered by tests.

**Estimate:** 5 points for a bounded status view; refine if the scope expands.

### P2 — Follow-on quality improvements

#### PB-11 — Evaluate skill-relationship quality and multilingual coverage

**User story:** As a candidate, I want related-skill matches to be useful and
understandable in supported languages so the score does not overstate evidence.

**Acceptance criteria**

- Build a reviewed evaluation set for direct, related, foundational, and
  missing-skill cases across French, Arabic, and supported aliases.
- Verify that relationship direction, strength, confidence, and evidence are
  represented correctly in score explanations.
- A score is never labelled as a hiring probability; zero required skills
  remain explicitly unscored.
- Preserve user-entered terms and make unresolved aliases reviewable rather
  than silently treating them as equivalent.

**Estimate:** 5 points

#### PB-12 — Improve cross-role responsive and accessible UX

**User story:** As a user on desktop or mobile, I want every role's main
navigation and forms to be usable with keyboard and assistive technology so I
can complete core tasks confidently.

**Acceptance criteria**

- Every visible navigation entry leads to a supported destination or is
  removed/renamed.
- Core candidate, employer, provider, ministry, and operator screens are
  checked at desktop and mobile breakpoints.
- Keyboard navigation, focus handling, labels, contrast, and French/Arabic
  text direction are checked on representative workflows.
- Findings and unresolved accessibility limitations are documented.

**Estimate:** 8 points

## Refinement notes

- Confirm the product goal and pilot target users with stakeholders before
  committing work.
- Recheck existing implementation and CI results during refinement; several
  items intentionally validate features that already exist.
- Split items larger than one sprint after the team agrees on its actual
  capacity and definition of done.
- Sprint planning should select a feasible subset from this ordered backlog;
  no sprint scope or delivery date is prescribed here.

## Repository references

- [Frontend role routing](../src/App.tsx)
- [Backend role permissions](../backend/app/permissions.py)
- [Candidate skill scoring](../backend/app/matching/scoring.py)
- [Public-data collector](../backend/app/data_pipeline.py)
- [Labour-data ingestion](../backend/app/ingest_labour_data.py)
- [Observatory API and marketplace workflows](../backend/app/marketplace.py)
- [Analytics suppression and metadata](../backend/app/analytics.py)
- [Employer planning API](../backend/app/planning.py)
- [Missions API](../backend/app/missions.py)
- [Professional services API](../backend/app/professional.py)
- [Service requests API](../backend/app/service_requests.py)
- [Backend test suite](../backend/tests/)
- [Product and role audit](./AUDIT.md)
- [Pilot release gates](./PILOT_RELEASE_GATES.md)
- [Labour-market data structure](./MINISTRY_LABOUR_MARKET_DATA_STRUCTURE.md)
- [Location data sources](./location-data-sources.md)
- [Current implementation task ledger](../TASKS.md)
