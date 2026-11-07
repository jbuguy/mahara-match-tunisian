# Mahara Match product functionality and user-role audit

**Reviewed:** 2026-11-07  
**Scope:** Current repository implementation: frontend navigation and screens, FastAPI endpoints, role permissions, persisted models, README claims, and `TASKS.md`. This is a code and product-scope audit, not a live deployment or user research study. “Available” means represented in the current code; services, database setup, seed data, and configuration may still be required to use it.

## Executive summary

Mahara Match currently has a strong candidate career-development workflow: profile building (including CV-assisted extraction), skill-based job matching, a career roadmap, interview practice, training discovery, applications, and a conversational assistant. Employers can manage an organisation and job offers and process applications. Training providers have a course catalogue and enrollment tracking. Ministry administrators have aggregate platform indicators. Operators have an audit view, while their advertised service controls are placeholders.

The current product is a functional prototype with server-side role/ownership checks and persistent records for core workflows. It is not yet a complete employment marketplace or a complete operational platform. The most important gaps are candidate discovery/application flow quality, employer applicant decision support, provider course management usability, incomplete admin/operator capabilities, identity and organisation lifecycle, and unfinished end-to-end validation called out in `TASKS.md`.

## 1. What each user type can currently do

| Role | Current implemented capabilities | Important boundaries and unfinished areas |
| --- | --- | --- |
| **Candidate** | Register and sign in; create/edit a structured profile; get CV-assisted profile extraction and review suggestions before saving; use career assistant chat with text and optional speech/transcription; keep, reopen, rename, search, and delete owned assistant sessions; see published-offer matches based on required-skill overlap; track a roadmap derived from missing skills; practice technical and behavioral interview questions, submit text or recorded answers, review/edit transcripts, and view progress/coaching; browse/pursue published courses; apply to offers and track application statuses. | Can register only as a candidate. No password recovery or account lifecycle controls are evident. Match score is informational required-skill overlap, not a hiring probability. Course recommendations exist in interview prep, but `TASKS.md` still marks their regression checks pending. Job discovery depends on employer-entered offers; authoritative Tunisia vacancy ingestion is absent. |
| **Employer** | Create and update a linked organisation profile; draft offer content with assistant suggestions; create and list own offers; view applicants to owned offers; update application status (submitted/reviewing/interview/hired/rejected); access role-specific assistant guidance. | No candidate search/proactive sourcing, shortlist/notes, structured interview scheduling, or outcome verification. Offer lifecycle moderation/expiry and organisation verification are not evident. Application outcome is employer-reported. |
| **Training provider** | Create and update own courses with metadata, skills, delivery/location/dates/capacity/price and draft/published/archived status; view course rosters; mark enrollment completion or withdrawal; access provider-oriented assistant guidance. | No demonstrated credential issuance, learner assessment, course content delivery, payments, waitlists, or course outcome reporting. `Catalogue de formations` and dashboard currently route to the same provider dashboard component, so catalogue/dashboard separation is weak. |
| **Ministry administrator** | View date-filtered aggregate indicators for registrations, offer skills, applications/statuses, employer-reported hiring outcomes, and training. Access role-oriented assistant guidance. | No candidate-level access by design. The README advertises referential management, suggestion review, dataset imports, and logged exports, but no corresponding UI or API is implemented. Indicators reflect platform data and employer reports, not national labour-market coverage or independently verified outcomes. |
| **Operator** | Read the audit-event view, which is designed to omit identifying/resource details and personal event data; access role-oriented assistant guidance. | `Services` is a placeholder; no service configuration or job-status route is implemented. Audit access is the only concrete operator workflow. Avoid exposing secrets through any future service controls. |

Shared capabilities include authentication, role-specific navigation, light/dark theme, responsive app shell, and floating assistant entry point. Role checks and ownership/organisation scoping are enforced server-side for implemented protected APIs. Five roles are defined: candidate, employer, ministry admin, training provider, and operator.

## 2. Value offered to each type of user

| Role | Current value proposition | Evidence and product limitation |
| --- | --- | --- |
| **Candidate** | A single place to turn skills and experience into relevant opportunities, a practical skill-gap plan, training options, and interview practice—with an assistant that can support French/Derja-oriented workflows and voice where configured. | The workflow is unusually broad for a prototype. Value depends on profile completeness and the quality/quantity of published offers and courses. Matching is a transparent baseline rather than a validated ranking model; labour-market retrieval does not currently query live course availability. |
| **Employer** | A lightweight way to publish skill-described roles and process applications, with AI-assisted drafting that can reduce the effort of writing an offer. | Applicant volume and quality depend on candidate adoption. There is no sourcing funnel, verification, hiring workflow beyond status updates, or verified outcome loop to establish employer ROI. |
| **Training provider** | A way to expose skills-oriented courses to candidates and manage enrollment/completion records, potentially linking training to career skill gaps. | Course discovery is present, but delivery, learner achievement evidence, and conversion/impact analytics are not. Skill alignment depends on providers maintaining useful skill metadata. |
| **Ministry administrator** | Aggregate visibility into activity, requested skills, applications, reported hiring, and training participation without access to individual candidate records. | Indicators can support pilot monitoring, not policy-grade labour-market conclusions: data are platform-generated, coverage may be sparse, and hiring outcomes are self-reported. Import/referential/export capabilities described elsewhere are absent. |
| **Operator** | A privacy-conscious way to inspect audit activity for operational oversight. | Operational value is currently narrow because service health/configuration and asynchronous job-status tools are not implemented. Liveness is process-only and explicitly does not indicate database readiness. |

## 3. Missing, incomplete, redundant, or improvable

### P0 — Close the current workflow and trust gaps

1. **Complete integration validation before adding more features.** `TASKS.md` leaves the assistant navigation flow unverified at desktop/mobile, assistant session checks pending after a guard change, interview-prep phases 7/8 checks pending, and phase 10 end-to-end integration/optimization incomplete. Close and record those checks; confirm current counts/statuses rather than relying on stale ledger totals.
2. **Make account and organisation setup dependable.** Candidate self-registration exists, but employer/provider/admin/operator onboarding appears to rely on seeded accounts and organisation links. Add a controlled invitation/approval and account recovery/lifecycle flow before real pilot users depend on access.
3. **Improve the opportunity-to-application journey.** Verify that offer detail, match explanation, eligibility, application confirmation, and status changes form a clear usable path. Add empty/error/stale states and clarify that match scores do not predict selection.
4. **Clarify data provenance and outcome meaning.** Prominently distinguish live employer-posted offers, synthetic development data, macro indicators, assistant-generated suggestions, and employer-reported hires. Do not imply comprehensive Tunisia vacancy coverage or independently verified employment impact.

### P1 — Improve role-specific usefulness

5. **Employer applicant workflow:** add useful application detail, shortlist/notes, clear status history, and a consistent interview follow-up process. Keep candidate private profile data scoped to an application and record sensitive access.
6. **Provider workflow:** separate catalogue management from dashboard reporting; add course discovery quality controls and learner progress/evidence if the pilot needs providers to demonstrate outcomes.
7. **Admin product scope:** decide whether referentials, suggestion review, dataset import, and logged export are actual pilot requirements. If so, build and audit those workflows; otherwise correct README permissions/product claims to the implemented aggregate-only admin scope.
8. **Operator product scope:** implement service/job status with safe secret handling and database/dependency readiness, or remove the `Services` navigation until supported. Keep process liveness distinct from readiness.
9. **Assistant continuity and quality:** finish navigation verification, document which roles receive which assistant behavior, and add a clear fallback when model/voice/RAG services are unavailable. The application-data context and retrieval coverage should be explicit, especially since current assistant RAG does not provide current course catalogue records.

### P2 — Reduce ambiguity and redundant UI

10. **Provider dashboard/catalogue duplication:** both navigation entries mount the same component. Give each a distinct task or combine them into one clear destination.
11. **Navigation/content mismatches:** operator `Services` currently lands on “En préparation”; this is a visible dead end. Audit every nav item against its actual screen for each role.
12. **Baseline product comparison:** older audit/README text describes early project state and broader planned capabilities. Keep historical baseline clearly dated, but make current implemented scope and explicitly planned scope easy to distinguish.
13. **Terminology and localization:** standardize French labels and clarify terms such as “opportunité,” “parcours,” and “candidature”; validate Derja/Arabic directionality, script rendering, and accessibility in real screens, not only component tests.

## Role and access-control consistency notes

- Backend permission definitions include ministry referential/import/export and operator service/job permissions, but current API route inventory does not expose those operations. A permission constant is not an implemented capability.
- README's role table currently overstates implemented admin and operator functions. Update it after deciding whether those features are intentionally deferred or are required for the product.
- The employer and provider records are attached through organisation memberships, but current UI/API flows are effectively single-organisation-per-account. If multi-user organisation teams are a goal, add explicit membership administration and test cross-member access.
- Admin aggregate indicators are present and intentionally avoid individual profiles. Keep minimum cohort/privacy safeguards in mind if future filters create small groups.
- The current liveness endpoint checks process responsiveness only. Do not present it as service or database readiness.

## Recommended next step

Run a focused stabilization milestone: finish the pending Task 12, Task 2, and Task 9 checks; audit every role navigation item against its destination and API; correct the README's overstated capabilities; then conduct a short task-based walkthrough with one seeded account per role. Use that evidence to select the next feature investment. Prioritize candidate application completion and employer/provider workflow feedback only after those journeys are verified end to end.

## Sources reviewed

- `TASKS.md` current focus, build order, outstanding checks, and project guardrails.
- `src/App.tsx` role-specific navigation and page routing.
- `src/workspaces.tsx` candidate, employer, and assistant workflows.
- `src/marketplace.tsx` dashboards, applications, courses, and organisation screens.
- `backend/app/main.py` authentication, profile, assistant, matching, roadmap, interview preparation, employer offer, and audit routes.
- `backend/app/marketplace.py` applications, courses/enrollments, and aggregate indicator routes.
- `backend/app/permissions.py` role permission matrix.
- `backend/app/models.py` persisted role and product entities.
- `README.md` product/API, data, and privacy claims.
