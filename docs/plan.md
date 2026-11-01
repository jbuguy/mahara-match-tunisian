# Mahara Match MVP plan

**Updated 31 October 2026 against the consolidated cahier des charges and the current repository.**

## Product priority

The next feature to flesh out and complete is the **trusted matching loop**:

> A candidate creates or corrects a profile without a CV, receives a reproducible and explainable ranking of eligible offers, and can submit an application while the matching context is preserved.

This is the most important MVP slice because it joins the three commitments in the cahier des charges: F1 (accessible profile), F2 (explainable matching), and the minimum useful part of F3 (a published employer offer). It should be completed and demonstrated before expanding mock interviews, training-center workflows, or ministry features.

The target is not a new matching algorithm. The target is a trustworthy end-to-end product path around the existing deterministic scorer: validated inputs, correct eligibility rules, clear explanations, secure ownership, resilient fallbacks, and tests.

## MVP definition of done

- [ ] A candidate can sign up, create or edit a profile without uploading a CV, review the proposed data, give the required consent, and save it.
- [ ] Skills and occupations use validated taxonomy codes where available; unknown values are visible and never silently treated as confirmed skills.
- [ ] The candidate can open a matches view containing only published, non-expired offers.
- [ ] Matching is deterministic and versioned. The current documented weights are technical skills 50%, experience 20%, soft skills 15%, and location 15%.
- [ ] Every match explains the component scores, matched requirements, missing or insufficient skills, and relevant data limitations. Age, gender, and origin never contribute to the score.
- [ ] A candidate can view an eligible offer, apply once, and see the application status and match snapshot later.
- [ ] An employer can create an offer with the required fields, review and edit the draft, and publish it explicitly. A draft or expired offer cannot enter candidate matching.
- [ ] A candidate cannot read another candidate's profile or application; an employer can access only its own offers and authorized applications.
- [ ] LLM, speech, or other external-service failure does not erase saved profile data or prevent manual profile completion.
- [ ] Automated tests cover scoring, eligibility, explanation consistency, application ownership/idempotency, publication rules, and the key data contracts.
- [ ] One manual demo is recorded with representative candidate, employer, published, draft, expired, and rejected-access cases.

## Current repository status

### Already present or substantially present

- [x] React/Vite candidate and employer workspaces, authentication routes, onboarding, profile editing, offers, applications, matches, and roadmap views.
- [x] Candidate-facing offer and match services, persisted match results, skill-gap data, and application flow.
- [x] Employer structured/form and conversational offer creation, draft review, explicit publication, and employer application views.
- [x] Shared taxonomy schemas/contracts and deterministic matching integration coverage in `back/tests/test_wp3_integration.py`.
- [x] Candidate voice/transcription infrastructure and CV import building blocks.
- [x] Training-provider routes/workspace and mock-interview UI exist as separate, incomplete or operationally dependent modules.

### Must be verified before calling the MVP complete

- [ ] Run the complete candidate-to-application journey against a running backend and frontend with realistic seeded data.
- [ ] Confirm that profile consent, correction, deletion, and sensitive-data access behavior work end to end.
- [ ] Confirm that only published and non-expired offers are returned by every candidate matching/discovery path, including cached or persisted results.
- [ ] Confirm score/explanation consistency and that the scoring formula/version are stored with the result.
- [ ] Confirm application duplicate prevention, status transitions, and ownership at the API boundary.
- [ ] Confirm employer ownership and verified-email publication requirements in both UI and API paths.
- [ ] Replace any UI-only claim that a non-discrimination guardrail is active unless an auditable rule engine and rule catalog are actually enabled. The cahier explicitly says it must be declared unavailable rather than simulated.
- [ ] Validate accessibility, mobile layout, keyboard navigation, French/Arabic/Derja language behavior, and manual fallbacks.

## Implementation plan: trusted matching loop

### Phase 0 — Baseline and contracts

- [ ] Map the actual routes, schemas, migrations, and frontend calls for profile, offers, matches, and applications.
- [ ] Seed a small deterministic fixture set: one candidate profile, two matching offers, one draft, one expired offer, one unknown skill, and one second user for authorization tests.
- [ ] Define the match-result contract, including `formula_version`, component scores, matched skills, gaps, missing-data indicators, and offer eligibility metadata.
- [ ] Decide and document retention/deletion behavior for profile, match, and application records used in the MVP demo.

**Exit:** fixture data reproduces the same expected ranking and every required endpoint has a documented request/response shape.

### Phase 1 — Candidate profile reliability (F1)

- [ ] Make manual profile creation the guaranteed path; preserve drafts across assistant/STT/LLM failures.
- [ ] Validate skill, occupation, language, experience, and governorate values against the shared taxonomy or mark them as unresolved.
- [ ] Show a review step before saving assistant/CV/audio-derived values; do not let generated content silently become confirmed profile data.
- [ ] Enforce explicit consent and implement or verify correction/deletion requests and candidate-only access.
- [ ] Add endpoint tests for missing profile, malformed values, unknown taxonomy values, consent, retry, and cross-account access.

**Exit:** a candidate can complete and save a useful profile with no CV and with every proposed value reviewable.

### Phase 2 — Matching correctness and explanations (F2)

- [x] Centralize the deterministic scoring formula and expose a version identifier with each result.
- [ ] Enforce eligibility at query and service layers: published status, non-expired date, valid taxonomy references, and any offer-specific candidate rules.
- [ ] Ensure only approved reference relationships contribute to skill similarity; unknown or missing data is represented as unknown rather than as a zero presented as certainty.
- [ ] Generate explanations from the same score inputs used by the scorer, not from an LLM or separately inferred text.
- [ ] Return matched requirements, missing/insufficient skills, component breakdown, and limitations in the API contract.
- [ ] Test stable ordering/tie behavior, formula changes, expired/draft exclusion, protected-attribute exclusion, and explanation/score consistency.

**Exit:** the same profile, offers, and formula version always produce the same ordered results and an auditable explanation.

### Phase 3 — Employer offer readiness (minimum F3)

- [ ] Require title, responsibilities, location, contract type, and required skills before publication.
- [ ] Validate suggested skills against the taxonomy and let the employer correct them.
- [ ] Keep draft, published, closed, and archived transitions explicit and server-authorized.
- [ ] Require employer email verification before publication and preserve an explicit review/confirmation action.
- [ ] Implement a rules-based non-discrimination guardrail for the agreed initial languages only, or mark the guardrail unavailable until its rule catalog is ready. Store auditable `guardrail_flags`; never let a hidden LLM decision publish or reject an offer.
- [ ] Test that edits, publication, expiry, closure, and archive status immediately affect candidate eligibility.

**Exit:** an employer can safely publish one valid offer, and a candidate can see it in matching only while it is eligible.

### Phase 4 — Application handoff

- [x] Allow a candidate to apply only to an eligible offer and prevent duplicate applications.
- [ ] Store the match-result/formula snapshot used at application time so later score changes do not rewrite history.
- [ ] Expose candidate application history only to that candidate and authorized employer users.
- [ ] Test allowed status transitions, unauthorized reads/updates, duplicate submission, closed-offer behavior, and sensitive-access audit events.

**Exit:** the complete candidate → match explanation → application → employer review path works with ownership enforced by the API.

### Phase 5 — Demo hardening and release gate

- [ ] Run backend tests and the frontend production build.
- [ ] Run a manual smoke test with seeded accounts and record failures by actor and route.
- [ ] Check responsive behavior, keyboard access, labels, empty/loading/error states, and language fallback.
- [ ] Check logs/secrets, migration status, external-service configuration, and absence of credentials in the browser or repository.
- [ ] Publish a short known-limitations note: complementary features may exist in the codebase but are not part of the completed MVP gate.

**Release gate:** all MVP definition-of-done items pass, or the unmet item is explicitly documented as a blocker rather than presented as complete.

## Deferred after the core loop

These remain valuable, but should not displace the trusted matching loop:

1. **Mock interview:** complete the existing candidate UI/backend integration, provider configuration, retention cleanup, rate limits, language evaluation, and privacy tests. It must remain private coaching and never become a hiring score.
2. **Training center:** finish provider verification, course lifecycle, approved-provider visibility, ownership tests, and index refresh rules before exposing courses in candidate matching or roadmaps.
3. **Employer depth:** applicant search/sorting, notes, bulk actions, calendar scheduling, delivery webhooks, and full French/Arabic localization.
4. **Ministry governance:** taxonomy review, imports, audit events, protected aggregates, and operational dashboards.

## Decisions required before expanding scope

- Confirm the launch languages for the full interface and for assistant/transcription output.
- Confirm the initial taxonomy sectors, occupations, and skill coverage for Tunisia.
- Confirm the formula versioning and policy for recalculating existing matches.
- Confirm data retention periods for profiles, CVs, transcripts, matches, applications, and audit events.
- Confirm the initial non-discrimination rule catalog, supported languages, severity levels, and human review policy.
- Confirm deployment, backups, private file storage, email provider, external AI provider, rate limits, and monitoring.

## Working order

1. Baseline routes, contracts, fixtures, and migration state.
2. Make candidate profile review/consent/manual fallback reliable.
3. Close matching eligibility, score versioning, explanation, and fairness tests.
4. Close employer publication and guardrail behavior.
5. Close application snapshot and authorization behavior.
6. Run the full release gate and only then resume mock-interview/training-center expansion.
