# Tunisia Labour-Market and Platform Data Structure

This document describes the data currently loaded into PostgreSQL for ministry
presentation and planning discussions. It distinguishes official public data,
historical training information, and activity recorded by Mahara Match.

## Current database load

| Group | PostgreSQL records | Purpose |
| --- | ---: | --- |
| Tunisia labour-market knowledge documents | 5 | National employment, unemployment, youth unemployment, agricultural investment jobs, and vocational training taxonomy |
| France comparison knowledge document | 1 | Comparative context only; not evidence of Tunisia demand |
| Search chunks created from the documents | 361 | Text available to the assistant and keyword retrieval |

Run-time data is also available in the application's relational tables.

## Official and public data

### National annual indicators

`worldbank-tn-unemployment`

| Field | Meaning | Presentation use |
| --- | --- | --- |
| `period` | Observation year | X-axis or reporting period |
| `value` | Annual unemployment estimate | Percentage rate |
| `unit` | `percent` | Add as a % indicator |
| `indicator` | Total labour-force unemployment definition | Describe the indicator accurately |
| `methodology` | Modelled ILO estimate | State that the figure is an estimate |
| `source_url` | World Bank source | Cite in charts and reports |

`worldbank-tn-youth-unemployment`

Uses the same structure as total unemployment, but applies to people aged 15-24.

`worldbank-tn-employment-to-population`

Uses the same structure, but reports employment as a percentage of the population
aged 15 and older. It is an employment participation measure, not a vacancy count.

### Agricultural jobs created

`tunisia-agridata-jobs-created`

| Field | Meaning |
| --- | --- |
| `period` | Year |
| `value` | Administrative count of jobs attributed to agricultural investment projects |
| `unit` | Jobs created through agricultural investment projects |
| `methodology` | Administrative investment-project count; not total employment or vacancies |

Use this series to discuss employment attributed to agricultural investment.
Do not extrapolate it to total Tunisian employment or to current hiring demand.

### Historical vocational specialities

`tunisia-vocational-specialties`

This source contains 345 records from 2017. Each record has:

| Field | Meaning |
| --- | --- |
| `specialty_code` | Training specialisation code |
| `specialty_fr` | French specialisation name |
| `specialty_ar` | Arabic specialisation name |
| `sector` | Sector |
| `subsector` | Subsector |
| `certificate` | Certificate type or code |
| `training_duration_years` | Historical programme duration, when supplied |
| `availability_status` | Labels the source as a historical list, not current course availability |

This list must not be presented as a current catalogue of training places.
Use live courses from `training_courses` for current supply.

## Knowledge database structure

The public observations are stored as readable documents in
`knowledge_documents` and split into searchable sections in
`knowledge_chunks`.

Key `knowledge_documents` fields:

| Field | Ministry meaning |
| --- | --- |
| `external_id` | Stable source identifier |
| `title` | Human-readable dataset or indicator title |
| `content` | Source observations and methodology in searchable text |
| `source` | Publishing organisation |
| `source_url` | Canonical source or series page |
| `category` | `labor_market` or `formation` |
| `subcategory` | Dataset classification |
| `country` | Tunisia or France |
| `source_updated_at` | Source update or retrieval-vintage date |
| `document_metadata` | Year range, observation count, licence, methodology, and source identifiers |
| `status` | `ready`, `pending`, or `failed` ingestion state |

## Application data to combine with the public indicators

### Candidate supply

`candidate_profiles`

- `user_id`
- `skills`
- `full_name`
- `location`
- `education`
- `experience`
- `professional_headline`

Presentation possibilities:

- Number and location of candidates declaring each skill.
- Supply of candidates by location.
- Candidate skills compared with skills required by published employers.
- Education or experience profiles by occupation and location.

Candidate personal data must be aggregated and de-identified before sharing
with ministry staff.

### Employer demand

`job_offers`

- `title`
- `description`
- `location`
- `required_skills`
- `preferred_skills`
- `employment_type`
- `workplace_arrangement`
- `positions_count`
- `salary_min`
- `salary_max`
- `application_deadline`
- `status`
- `published_at`

Use only published offers for current demand reporting. Sum `positions_count`
only when each offer is confirmed and avoid counting drafts, closed offers, or
duplicates unless the report explains that inclusion.

### Applications and recruitment outcomes

`job_applications`

- `candidate_id`
- `job_offer_id`
- `status`
- `created_at`
- `updated_at`

This table can support application volumes and employer outcome funnels. For
example, compare applications, submitted candidates, shortlists, interviews,
offers, and hires if all relevant status history is available.

### Current training supply

`training_courses`

- `title`
- `summary`
- `skills`
- `delivery_mode`
- `location`
- `starts_on`
- `ends_on`
- `duration_hours`
- `capacity`
- `price_tnd`
- `status`
- `published_at`

`course_enrollments`

- `candidate_id`
- `course_id`
- `status`
- `created_at`

Use only published courses for the ministry dashboard. Join enrollments to
courses to measure demand by skill, location, provider, and course capacity.

## Recommended ministry dashboard

| Dashboard view | External data | Application data | Question answered |
| --- | --- | --- | --- |
| National labour context | World Bank unemployment and employment ratio | Published job offers, applications | Is platform demand moving against national labour-market trends? |
| Youth employment | Youth unemployment | Candidate profiles and applications | Which skills or locations need stronger youth pathways? |
| Skills gap | Historical terminology and national indicators | Candidate skills, offer skills | Where do candidate supply and employer requirements differ? |
| Training alignment | 2017 speciality taxonomy | Current courses, enrollments, offer skills | Which training areas match employer demand? |
| Geographic view | National indicators | Offer locations, candidate locations, course locations | Which governorates need jobs, courses, or placement support? |
| Investment jobs | Agricultural jobs created | Agricultural offers and applications | How does platform activity relate to recorded investment employment? |

## Safe reporting rules

- Treat World Bank unemployment series as modelled estimates, not registrations.
- Treat agricultural job creation as project-attributed jobs, not vacancies.
- Treat training specialities as a historical taxonomy, not a current course list.
- Treat French data as comparative context only.
- Do not combine unrelated units into one metric.
- Do not infer individual hiring probability from national trends.
- Only report aggregate candidate counts to ministry users; protect personal data.
- Include source, period, methodology, and retrieval date on every chart.
