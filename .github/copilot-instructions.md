# Mahara Match project rules

## Ministry Observatory

- Build the Ministry Labour Observatory in French while keeping code, comments, commit messages, identifiers, and technical documentation in English.
- Follow existing repository conventions, migrations, and test setup.
- Never expose individual candidate data through any endpoint. Ministry data must contain only aggregates.
- Suppress any server-side aggregate computed from fewer than 5 people. Return `null` with `suppressed: true`; do not rely on UI-only suppression.
- Keep external indicators separate from platform metrics, including separate chart series and axes when units or sources differ.
- Use honest labels:
  - World Bank unemployment data is a modelled ILO estimate.
  - Hires are declared by employers.
  - Agricultural jobs are project-attributed jobs, not vacancies.
  - The 2017 vocational specialities are a historical taxonomy, not current courses.
  - French data is comparison context only.
- Every chart and metric response must include source metadata: `source`, `source_url`, `period`, `methodology`, and `retrieved_at`.
- Count only published job offers and published courses. Exclude drafts, closed offers, and duplicate offers unless an explicit requirement states otherwise.
- Preserve existing endpoints until the rebuilt page replaces them.
- Add focused tests for every new endpoint and migration.
