# Training Center Actor Plan

## Goal

Add **training center** (organisme de formation) as a first-class actor in Mahara Match. Authorized staff should be able to manage their organization and course catalog, and candidates should be able to discover relevant training. The center actor manages training information; the platform remains responsible for account security and any provider accreditation/verification.

## Existing foundations and gaps

- The shared data model already includes the `training_provider` user role in `back/mahara_data/enums.py`.
- `TrainingProvider`, `TrainingCourse`, and `TrainingCourseSkill` are defined in `back/mahara_data/db/models/training.py`; the provider row can be linked to a user through `user_id`.
- Training course and certification payloads are defined in `back/mahara_data/schemas/training.py`.
- Course catalog records already feed matching knowledge and candidate roadmaps through `back/app/features/matching/rag.py` and matching models.
- The production frontend currently exposes candidate, employer, and ministry workspaces in `front/src/App.tsx`; it has no training-center workspace.
- Registration/sign-in choices currently focus on candidate and employer. The platform needs a safe provider registration and verification flow before self-service publishing is enabled.
- Confirm that migration enum values and role checks stay aligned before adding routes. Existing shared schemas may be ahead of the live application surface.

## Proposed first release

1. **Training center account:** Add a center registration/sign-in path, a provider profile, and a pending-verification state. Capture organization name, provider type, location/governorate, website/contact, and accreditation reference where applicable.
2. **Verification and access:** Let authorized platform staff review provider details and approve, reject, or suspend the organization. A pending or suspended center cannot publish courses. Do not treat a self-entered accreditation reference as verified accreditation.
3. **Center workspace:** Add a dedicated dashboard showing provider verification status, published courses, drafts, and basic catalog completeness.
4. **Course management:** Let staff create, edit, preview, publish, archive, and restore courses owned by their provider. Capture title, description, modality, duration, cost/free status, language, governorate, certification, and skills taught with target levels.
5. **Candidate discovery:** Surface active, approved-provider courses in candidate training recommendations and skill roadmaps. Provide clear links/contact details and course availability information only when verified and present in the catalog.
6. **Certification verification (later in MVP):** Define a provider-scoped workflow for checking a candidate-submitted certificate. A center can verify only certificates associated with its organization/courses; record decision, reviewer, and timestamp, and allow platform audit/review.

## Roles and permissions

- **Training provider staff:** Read/update their own provider profile and manage courses belonging to that provider. They cannot access another provider's drafts, candidate profiles, mock interview results, or private candidate data.
- **Provider owner/admin:** Manage that center's staff access and submit verification details, subject to platform identity/account support.
- **Platform verifier/admin:** Approve, reject, suspend, or reinstate providers; review accreditation evidence; audit changes and certificate verification decisions.
- **Candidate:** Browse published courses and submit a certificate for verification. Candidate data is shared with a provider only when needed for a verification request and with clear user-facing notice.
- **Employer and ministry users:** No access to private provider drafts or candidate certification documents. Ministry reporting, if later needed, should use aggregated catalog data.

Every provider API must enforce both the `training_provider` role and ownership of the provider/course resource. Hiding links in the UI is not authorization.

## Suggested implementation shape

### Identity and database

- Reconcile the live user/account model with the shared `UserRole.TRAINING_PROVIDER` role, including signup/login, token claims, effective role lists, and role migration synchronization.
- Add/confirm provider lifecycle fields such as `verification_status`, submitted/verified timestamps, verifier identity, and suspension reason. Keep evidence documents in the existing document/storage approach with strict access controls rather than public URLs.
- Enforce a single ownership path from authenticated user to provider. Add constraints/indexes and migration/backfill behavior for existing provider records, including unclaimed catalog entries.
- If centers need multiple staff accounts, model explicit provider membership and owner/admin/editor roles rather than sharing one login. Keep the first release single-owner only if multi-staff scope is deferred deliberately.

### Backend

- Add a provider feature module with authenticated routes for own profile, verification submission/status, course CRUD, publish/archive actions, and certificate review when that workflow is included.
- Reuse the existing course contracts and skill taxonomy resolution; validate required skills and target levels on the server.
- Scope list/get/update/delete operations by the authenticated user's provider ID. Return only published courses in public/candidate discovery APIs.
- Record audit events for provider approval/suspension, course publication changes, and certificate decisions. Never expose certificate document contents through normal catalog endpoints.
- Define validation for course dates/intakes and availability only if those fields are introduced; do not invent details for legacy catalog rows.

### Frontend

- Add an actor selection/signup path for training centers and a pending-verification state that explains what is needed to publish.
- Add protected routes and navigation for the provider dashboard, profile, course list, course editor, and preview.
- Support drafts, validation errors, publish confirmation, archive confirmation, empty states, and mobile/keyboard access.
- Keep candidate course discovery separate from provider management. Show provider verification state, course cost/modality/language/location, taught skills, and a clear way to contact/apply only when the catalog supplies it.

## Privacy, quality, and operations

- Collect only organization and staff data needed to operate the catalog. Keep candidate information private by default.
- Explain provider verification and course publication rules before submission. Provide a correction/contact path for rejected or suspended providers.
- Track catalog freshness and flag stale courses for provider reconfirmation; do not silently imply that old offers remain open.
- Prevent unpublished, suspended-provider, and rejected-provider courses from candidate search, RAG answers, embeddings, and roadmaps. Refresh or remove indexed content when publication state changes.
- Keep changes auditable, and define retention for accreditation evidence and certificate documents before enabling uploads.

## Delivery phases

1. **Foundation:** Align account roles and migrations; define provider verification lifecycle, ownership rules, and route authorization.
2. **Provider catalog MVP:** Center registration/profile submission, admin verification, provider workspace, and course CRUD/publish/archive.
3. **Candidate integration:** Discover approved published courses in matching/roadmaps and ensure indexes refresh on catalog changes.
4. **Certification workflow:** Add candidate submission and provider-scoped verification with audit trail and privacy controls.
5. **Operational hardening:** Review access boundaries, concurrent staff needs, stale catalog handling, accessibility, audit coverage, and migration of existing providers/courses.

## Decisions to make before implementation

- Is “training center” the user-facing label, with `training_provider` remaining the internal role name?
- Which authority verifies centers and what evidence is required for public, private, and NGO providers?
- Should the first release support multiple staff members per center or one account per center?
- Are candidates only discovering courses in the first version, or should they also apply/enroll through the platform?
- Which course fields are required for publishing, especially language, cost, location, intake dates, and contact details?
- Should provider staff verify candidate certifications in the first release or only manage the catalog?

## Acceptance criteria

- A provider account can be created and linked to exactly the authorized provider organization; pending providers cannot publish.
- Authorized platform staff can verify, reject, suspend, and reinstate a provider, with actor and timestamp recorded.
- Provider staff can manage only their organization's courses; unauthorized cross-provider access is denied by the API.
- Only active courses from approved providers appear in candidate discovery, matching context, and roadmaps; archiving or suspension removes them from those surfaces.
- Candidates can see enough course detail to judge relevance and can distinguish provider verification status.
- Candidate profile data and certificate documents are not exposed to providers unless the candidate initiates a clearly explained verification request.
- Existing provider/course records have an explicit migration and visibility policy, and catalog changes are reflected in search/embedding indexes.
