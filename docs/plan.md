# Feature Plan and Current Status

**Checked against the repository on 15 October 2026.** This plan tracks the candidate mock interview and the training-center actor, and records the recent conversion of the main product screens to React. A checked item means code exists; it does not imply the feature is production-verified or complete end to end.

## 1. React application screens

### Implemented

- [x] Candidate portal is a React route with profile, opportunities, applications, profile editing, offer details, and matching-roadmap views (`front/src/App.tsx`).
- [x] Candidate portal uses the existing profile, offer, application, matching, and roadmap APIs; candidate sign-in and onboarding lead to this route.
- [x] Employer workspace is a React route with employer offers, applications, hiring decisions, and the conversational offer-generation/review/publish flow.
- [x] Signup is routed to the React signup form. Candidate, employer, and invited training-provider sign-in routes use React.
- [x] `/dashboard` redirects to the candidate portal instead of showing the old role-state demo page.
- [x] Removed the standalone dashboard, employer, and signup HTML pages and their iframe route component.
- [x] Added responsive styling for candidate, employer, and training-center workspaces in `front/src/styles.css`.

### Still needed

- [ ] Install frontend dependencies and run the production TypeScript/Vite build; this has not yet been verified because `tsc` is unavailable in the current workspace.
- [ ] Manually verify candidate, employer, signup, and training-provider flows against a running backend and representative accounts.
- [ ] Add frontend/backend integration coverage for offer creation and publishing, application decisions, and profile updates.
- [ ] Review keyboard navigation, screen-reader labels, responsive layouts, and localized text for every new React route.

## 2. AI mock interview

### Existing building blocks

- [x] React/Vite candidate app and candidate navigation exist (`front/src/App.tsx`).
- [x] Shared OpenAI-compatible chat completion client exists (`back/shared_llm/client.py`).
- [x] Candidate voice transcription endpoint and in-memory audio processing exist (`back/app/features/employee/routers/assistant.py`, `back/app/features/employee/services/voice.py`).
- [x] Candidate occupation, skill, profile, and job-match data are available to existing app features.

### Feature work still needed

- [ ] Add a candidate-only mock interview page, setup flow, navigation link, and route.
- [ ] Generate role-focused questions one at a time, with optional follow-up questions.
- [ ] Accept typed responses and preserve interview state for the current session.
- [ ] Add audio recording with explicit microphone consent, transcript correction, and retry/error states.
- [ ] Generate structured feedback on understanding, relevance, specificity, and answer structure, with evidence and practical suggestions.
- [ ] Add optional, clearly explained confidence coaching; do not infer confidence from face, accent, or demographic traits.
- [ ] Add a final review and candidate-controlled retry flow; do not create a hiring score or pass/fail result.
- [ ] Keep interview results private from employers and matching/ranking features; do not persist raw audio/video by default.
- [ ] Validate model output, provider failure behavior, language quality, accessibility, and privacy behavior.
- [ ] Consider candidate-controlled video playback only after the text/audio experience is validated; no face-based confidence analysis.

**Current status:** Reusable LLM and transcription infrastructure exists, but no mock-interview feature, interview-session API, or review UI has been implemented.

## 3. Training-center actor

### Existing foundations

- [x] Shared `training_provider` user role, provider/course/course-skill/certification models, and training schemas exist.
- [x] Training-course records are used by matching knowledge and roadmap features.
- [x] Added training-provider password sign-in at `/training-providers/login`; provider accounts must be provisioned and linked by MFPE.
- [x] Added authenticated, provider-owned APIs for reading the linked center, listing its courses, creating courses, and toggling course availability (`back/app/features/training/router.py`).
- [x] Provider APIs enforce the `training_provider` role and scope course operations to the linked provider; course skills must come from the validated taxonomy.
- [x] Added a React training-center workspace with dashboard, accreditation reference display, course catalog, course creation, availability controls, statistics, settings, support, and guide views (`front/src/App.tsx`).
- [x] Added a training-center sign-in choice and Vite development proxy route.

### Still needed

- [ ] Add a controlled provider onboarding/linking workflow; current provider login works only for a verified user with a `TrainingProvider.user_id` association already provisioned.
- [ ] Add provider verification lifecycle fields and reviewer workflows. The current accreditation reference is informational and must not be shown as verified status.
- [ ] Add edit, draft, preview, publish, archive, and restore workflows for courses; the current API creates active courses and toggles availability.
- [ ] Enforce that only approved-provider courses enter candidate discovery, matching context, roadmaps, and embeddings. The current training model/API has no provider approval state.
- [ ] Add candidate-facing course details and application/enrollment only after the required course availability and contact data are defined.
- [ ] Add audit events for provider/course administration and authorization tests for cross-provider access.
- [ ] Define migrations and a visibility policy for existing provider/course records.
- [ ] Add backend and frontend coverage for provider login, unlinked providers, course validation, ownership, and availability changes.

**Current status:** The center workspace and limited provider-scoped catalog API are implemented. Account provisioning/linking, accreditation approval, full course lifecycle, audit coverage, and approved-course candidate discovery remain outstanding.

## Recommended next steps

1. [ ] Install the frontend dependencies and run the TypeScript/Vite production build; fix compile errors before adding more UI.
2. [ ] Start the backend and frontend and manually exercise the candidate and employer flows with test accounts, including offer creation/publishing and application status changes.
3. [ ] Decide and implement the MFPE-controlled training-provider provisioning and approval lifecycle; until then, create/link one authorized provider account in the development database for UI verification.
4. [ ] Add training-provider API tests for role checks, provider ownership, course creation, taxonomy validation, and availability changes.
5. [ ] Implement provider course draft/review/publish lifecycle and prevent unapproved courses from candidate-facing discovery and RAG.
6. [ ] Revisit candidate discovery to surface real training courses and clearly distinguish verified provider status.
7. [ ] Build the candidate mock interview as a separate feature after agreeing on languages, question design, feedback boundaries, and audio retention.

See the detailed proposals in [mock-interview-plan.md](./mock-interview-plan.md) and [training-center-actor-plan.md](./training-center-actor-plan.md).
