# Changelog

## Unified Assistant

- Added one Claude-style Assistant workspace for all authenticated roles.
- Added employer-only project conversations, project rail and contextual project panel.
- Added hash routes `#assistant` and `#assistant/project/:id`.
- Added browser voice input to the unified composer and floating assistant, plus browser read-aloud actions for assistant replies.
- Fixed the ministry administration navigation accent mismatch.
- Added migration `0022_planning_messages` and organisation-scoped planning message persistence.

## API

- `GET /employer/planning-sessions/{session_id}/messages`
- `POST /employer/planning-sessions/{session_id}/messages`
- Planning summary, document context, workforce analysis, recommendation review, and approved recommendation draft-offer endpoints.
- Added planning migration `0023_planning_recommendations`.

## Environment

- No new environment variables were required. Existing assistant provider configuration remains in use.
