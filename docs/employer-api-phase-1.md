# Employer API — Phase 1

All endpoints below require an authenticated employer. Application, offer, invitation, and draft data are scoped to that employer. Timestamps are ISO-8601; UTC timestamps use `Z`.

## Dashboard

`GET /api/v1/employer/dashboard`

Returns an aggregated response without requiring the client to combine multiple requests:

```json
{
  "kpis": {
    "active_offers": 1,
    "applications_total": 12,
    "shortlisted": 3,
    "hired": 1,
    "average_match_score": 78.25,
    "next_interview_at": "2026-11-06T09:00:00Z"
  },
  "attention": [
    {
      "type": "new_applications",
      "count": 2,
      "severity": "high",
      "target_route_hint": "/employer/applicants?status=submitted",
      "sample_ids": ["application-uuid"]
    }
  ],
  "top_candidates": [
    {
      "application_id": "application-uuid",
      "candidate_name": "Candidate",
      "offer_title": "Developer",
      "score_global": 91.5,
      "status": "submitted"
    }
  ],
  "offers_snapshot": [
    {
      "offer_id": "offer-uuid",
      "title": "Developer",
      "applications_count": 4,
      "top_match_score": 91.5,
      "expires_at": "2026-12-01T00:00:00Z"
    }
  ],
  "latest_benchmarkable_offer": {
    "offer_id": "offer-uuid",
    "occupation_code": "occupation-code",
    "governorate_code": "TN-11"
  }
}
```

`average_match_score` and `next_interview_at` are `null` when no qualifying rows exist; `latest_benchmarkable_offer` is `null` when no published offer has both an occupation and governorate. Attention items are ordered: new applications, shortlisted without an active invitation, offers expiring within seven days, unfinished drafts, then profile readiness. `sample_ids` holds record IDs, except `profile_readiness`, where it names incomplete fields (`email_verified`, `company_verified`, `tax_id`, `governorate_code`, `website`). “New” applications are derived from the initial `submitted` status; viewing an application is not separately recorded.

## Applications

`GET /api/v1/employer/applications`

With no query parameters, this keeps the existing response: an array of applications. Supplying any filter or pagination parameter returns:

```json
{
  "items": [
    {
      "application_id": "application-uuid",
      "candidate_name": "Candidate",
      "offer_title": "Developer",
      "score_global": 81.0,
      "status": "submitted",
      "applied_at": "2026-11-04T10:00:00Z",
      "employer_contact_consent": true,
      "gaps_summary": ["French", "Project management"]
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 25,
  "next_page": null
}
```

Supported query parameters: `offer_id`, repeatable `status`, `min_score` (0–100), `sort` (`applied_at` or `score_global`), `page` (1-based), and `limit` (1–100). The existing `/api/v1/employer/applications/page` route remains available.

## Interviews

`GET /api/v1/employer/interviews?status=sent&upcoming=true`

`status` is one of `queued`, `sending`, `sent`, `failed`, or `cancelled`; `upcoming=true` includes only meeting times at or after the current time. Returns an array of `{ invitation_id, application_id, candidate_name, offer_title, meeting_at, timezone, status }`. `sent` is recorded by the delivery worker only after the email provider accepts delivery, with `sent_at` recorded.

## Offer counts and editor catalogs

- `GET /api/v1/employer/offers/counts` returns `{ "all": 4, "published": 2, "drafts": 1, "archived": 1 }`. `all` includes offer records plus unfinished agent-session drafts; `drafts` counts sessions whose draft is absent or not published.
- `GET /api/v1/employer/catalogs/skills?q=dev&limit=20` returns an array of `{ skill_code, label }`, searching validated skills only.
- `GET /api/v1/employer/catalogs/languages` returns `{ languages: [{ code, label }], levels: [{ level, label }] }`. Languages are `ar-TN`, `ar`, `fr`, and `en`; proficiency levels are 1–4 (beginner through expert).

## Salary benchmark

- Canonical: `GET /api/v1/employer/salaries?occupation_code=...&governorate_code=TN-11`
- Deprecated alias: `GET /api/v1/employer/market/salaries` (same query parameters and response)

The response schema has `status: "available" | "suppressed" | "unavailable"` and shared occupation/area/period fields. Salary values and sample size are present for available data; suppressed and unavailable responses explain the reason and do not estimate a value.

## Offer updates, invitations, and decisions

- `PUT /api/v1/employer/offers/{offer_id}` accepts and returns `expires_at` as a timezone-aware ISO-8601 timestamp normalized to UTC. A timestamp without an offset is rejected. Skill taxonomy failures return a structured `detail` with `code`, `field`, and invalid skill codes; malformed skill or language structures return FastAPI validation details.
- `PATCH /api/v1/employer/offers/{offer_id}/status` reopens a closed offer only when its existing expiry is in the future or a future `expires_at` is supplied. Past expiry returns `409` with code `expired_offer`.
- `POST /api/v1/employer/applications/{application_id}/interviews` returns `409` with code `employer_contact_consent_required` when consent is absent, and `422` with code `meeting_time_in_past` for past meeting times.
- `PATCH /api/v1/employer/applications/{application_id}` remains the decision endpoint. Repeating an identical decision returns the existing application status without adding duplicate feedback.

No database migration is required. The API schema is exposed through FastAPI OpenAPI; no generated frontend client exists in this repository. Supported language options are returned from an explicit catalog because the repository stores language codes on offers and profiles but has no normalized language catalog table.
