# Feature Plan and Current Status

**Checked against the repository on 12 October 2026.**

This checklist tracks the two proposed features: an AI mock interview for candidates and a training-center actor. Checked boxes mean the capability already exists in the codebase; they do not mean the complete feature is done.

## 1. AI mock interview

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

**Current status:** The app has reusable LLM and transcription infrastructure, but no candidate mock interview feature, route, session API, or review UI was found.

## 2. Training-center actor

### Existing building blocks

- [x] Shared `training_provider` user role exists (`back/mahara_data/enums.py`; database enum in `migrations/20260921000000_wp1_shared_schema.sql`).
- [x] Training provider, course, course-skill, and candidate-certification models exist (`back/mahara_data/db/models/training.py`).
- [x] Training course and certification schemas exist (`back/mahara_data/schemas/training.py`).
- [x] Training catalog data is used by matching knowledge/roadmap features (`back/app/features/matching/rag.py`).

### Feature work still needed

- [ ] Add training-center registration/sign-in and link a provider account securely to one organization.
- [ ] Define provider verification lifecycle (pending, approved, rejected, suspended) and authorized reviewer actions.
- [ ] Add provider ownership and staff membership rules; enforce authorization and ownership on every provider API.
- [ ] Add a training-center workspace for provider profile, verification status, and course catalog.
- [ ] Add course create/edit/preview/publish/archive actions scoped to the owning center.
- [ ] Restrict candidate discovery, matching context, and roadmaps to active courses from approved providers.
- [ ] Refresh/remove search and embedding content when course publication or provider status changes.
- [ ] Add candidate-facing course details and clear provider verification status.
- [ ] Decide whether certification verification and multi-staff accounts are in the first release; add audit trails and strict document access if included.
- [ ] Define migration and visibility behavior for existing provider/course records.
- [ ] Add authorization, lifecycle, catalog freshness, privacy, and UI coverage.

**Current status:** The role, database structures, and schemas exist, but no training-center registration, workspace, provider management API, verification workflow, or provider-facing course CRUD was found. Existing course catalog integration does not provide a self-service center experience.

## Suggested sequence

1. [ ] Resolve product choices: launch languages and audio scope for mock interviews; provider verification authority, account model, and course publishing requirements for centers.
2. [ ] Build the mock-interview typed prototype and the training-provider identity/authorization foundation.
3. [ ] Add mock-interview audio and the provider course-management workspace.
4. [ ] Connect approved published courses to candidate discovery and roadmap surfaces.
5. [ ] Evaluate both features for quality, privacy, accessibility, authorization boundaries, and provider/model failure handling.

See the detailed proposals in [mock-interview-plan.md](./mock-interview-plan.md) and [training-center-actor-plan.md](./training-center-actor-plan.md).
