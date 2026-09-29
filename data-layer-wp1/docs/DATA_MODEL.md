# WP1 — Data Model Reference

**Schema version 1.0.** Sources of truth:
- SQL: [`supabase/migrations/20260921000000_wp1_shared_schema.sql`](../../supabase/migrations/20260921000000_wp1_shared_schema.sql)
- ORM: [`mahara_data/db/models/`](../mahara_data/db/models/)
- JSON contracts: [`mahara_data/schemas/`](../mahara_data/schemas/), exported to [`contracts/`](../contracts/)

`tests/test_migration_sync.py` checks that the SQL and the ORM have the same tables, columns, nullability, foreign keys and enum values.

## Conventions

| Topic | Rule |
|---|---|
| Primary keys | `uuid` with `gen_random_uuid()`. Exceptions: `governorates.code` (natural key), `audit_logs.id` (bigint identity), and association tables (composite key) |
| Time | `timestamptz`. `created_at` on every entity; `updated_at` kept current by the `set_updated_at` trigger |
| Codes | Skills `SK-####`, occupations `OC-####`, sectors `SEC-*`, governorates ISO 3166-2:TN (`TN-11` … `TN-83`) |
| Levels | Proficiency is an integer from 1 to 4: 1 beginner, 2 intermediate, 3 advanced, 4 expert |
| Scores | `numeric(5,2)` between 0 and 100 |
| Money | `numeric(10,2)` in TND |
| Enums | Postgres enum types store the lower-case **values** (e.g. `cv_upload`, `1-10`) |
| JSONB | Only for lists and semi-structured data (labels, languages, transcripts, NER output). Never for anything used as a join key |
| PII | Only in `candidate_pii`, `users` (contact fields) and `employers` (business contact) |
| Deletion | Child rows cascade from `candidates`, `job_offers`, `match_results` and `roadmaps`. Candidates are first soft-deleted (`deleted_at`) |

## Entity-relationship diagrams

### Taxonomy and reference

```mermaid
erDiagram
    skill_categories ||--o{ skill_categories : parent
    skill_categories ||--o{ skills : groups
    skills ||--o{ skill_relations : source
    skills ||--o{ skill_relations : target
    skills ||--o{ skill_suggestions : "resolved to"
    sectors ||--o{ sectors : parent
    sectors ||--o{ occupations : contains
    occupations ||--o{ occupation_skills : requires
    skills ||--o{ occupation_skills : "required by"
    users ||--o{ skills : validates

    skills {
        uuid id PK
        varchar code UK "SK-####"
        varchar label_fr
        varchar label_ar
        varchar label_derja
        jsonb alt_labels
        skill_type skill_type
        taxonomy_status status
        int version
    }
    occupations {
        uuid id PK
        varchar code UK "OC-####"
        varchar isco_code
        varchar title_fr
        varchar title_ar
        uuid sector_id FK
    }
    skill_suggestions {
        uuid id PK
        varchar normalized_label UK
        ingestion_source source
        int occurrences
        suggestion_status status
        uuid resolved_skill_id FK
    }
    governorates {
        varchar code PK "TN-11"
        varchar name_fr
        varchar name_ar
    }
```

### Candidates

```mermaid
erDiagram
    users ||--o| candidates : "account of"
    candidates ||--|| candidate_pii : "identity (restricted)"
    candidates ||--o{ candidate_skills : has
    skills ||--o{ candidate_skills : ""
    candidates ||--o{ candidate_experiences : has
    candidates ||--o{ candidate_educations : has
    candidates ||--o{ candidate_desired_occupations : wants
    occupations ||--o{ candidate_desired_occupations : ""
    candidates ||--o{ conversation_sessions : "onboarded via"
    candidates ||--o{ documents : uploads
    governorates ||--o{ candidates : "lives in"

    candidates {
        uuid id PK
        onboarding_path onboarding_path
        literacy_level literacy_level
        varchar governorate_code FK
        jsonb mobility_governorates
        education_level education_level
        numeric years_experience
        jsonb languages
        text service_offer
        jsonb raw_profile
        timestamptz consent_given_at
        timestamptz deleted_at
    }
    candidate_pii {
        uuid candidate_id PK,FK
        varchar full_name
        varchar email
        varchar phone
        date date_of_birth
        varchar gender
    }
    candidate_skills {
        uuid candidate_id PK,FK
        uuid skill_id PK,FK
        smallint level "1-4"
        skill_source source
        numeric confidence "0-1"
    }
    conversation_sessions {
        uuid id PK
        conversation_channel channel
        jsonb transcript "redacted"
        jsonb appetence
    }
```

### Employers, offers, applications, matching

```mermaid
erDiagram
    employers ||--o{ job_offers : publishes
    job_offers ||--o{ job_offer_skills : requires
    skills ||--o{ job_offer_skills : ""
    candidates ||--o{ match_results : scored
    job_offers ||--o{ match_results : scored
    match_results ||--o{ skill_gaps : reveals
    candidates ||--o{ applications : submits
    job_offers ||--o{ applications : receives
    match_results ||--o{ applications : "score snapshot"
    applications ||--o{ hiring_feedback : "decided by"
    candidates ||--o{ roadmaps : follows
    roadmaps ||--o{ roadmap_items : "ordered steps"
    training_courses ||--o{ roadmap_items : suggests

    job_offers {
        uuid id PK
        uuid employer_id FK "null = ministry feed"
        varchar title
        uuid occupation_id FK
        contract_type contract_type
        varchar governorate_code FK
        numeric min_years_experience
        offer_status status
        jsonb guardrail_flags
    }
    job_offer_skills {
        uuid job_offer_id PK,FK
        uuid skill_id PK,FK
        requirement_level requirement
        smallint min_level
    }
    match_results {
        uuid id PK
        numeric score_global
        numeric score_hard_skills "50%"
        numeric score_experience "20%"
        numeric score_soft_skills "15%"
        numeric score_location "15%"
        jsonb weights
        varchar model_version
    }
    skill_gaps {
        uuid match_result_id FK
        uuid skill_id FK
        gap_type gap_type
        smallint required_level
        smallint current_level
    }
    applications {
        uuid id PK
        application_status status
        uuid match_result_id FK
    }
    hiring_feedback {
        uuid id PK
        hiring_decision decision
        smallint match_quality "1-5"
    }
```

### Training, market data, platform

```mermaid
erDiagram
    training_providers ||--o{ training_courses : offers
    training_courses ||--o{ training_course_skills : teaches
    skills ||--o{ training_course_skills : ""
    candidates ||--o{ candidate_certifications : earns
    training_courses ||--o{ candidate_certifications : ""
    documents ||--o{ candidate_certifications : proves
    market_datasets ||--o{ market_indicators : contains
    documents ||--o{ market_datasets : "raw file"
    ingestion_jobs ||--o{ market_datasets : "loaded by"
    documents ||--o{ ingestion_jobs : input

    documents {
        uuid id PK
        document_type doc_type
        varchar storage_path
        varchar sha256
        processing_status processing_status
        bool pii_redacted
        text redacted_text
        jsonb extraction
    }
    ingestion_jobs {
        uuid id PK
        ingestion_source source
        processing_status status
        varchar pipeline_version
        int records_ok
        int records_failed
        jsonb errors
    }
    embeddings {
        uuid id PK
        embedding_entity entity_type
        uuid entity_id
        varchar model_name
        vector embedding "768"
        varchar content_hash
    }
    market_indicators {
        uuid id PK
        market_indicator_type indicator_type
        uuid occupation_id FK
        uuid skill_id FK
        varchar governorate_code FK
        date period_start
        numeric value
        varchar unit
    }
```

## Table catalog

### Reference & accounts
| Table | Purpose | Key constraints |
|---|---|---|
| `governorates` | The 24 governorates (seeded by the migration) | PK `code` |
| `sectors` | Economic sectors (tree) | `code` unique |
| `users` | Accounts for every role; `role` drives RBAC | email or phone required; both unique |

### Taxonomy
| Table | Purpose | Key constraints |
|---|---|---|
| `skill_categories` | Skill category tree | `code` unique |
| `skills` | Skills ontology with FR/AR/Derja labels, synonyms, type, status, version | `code` unique |
| `skill_relations` | broader / related / equivalent links | PK (source, target, type); no self-reference |
| `skill_suggestions` | Unknown labels waiting for admin review | `normalized_label` unique |
| `occupations` | Occupation referential (national code + ISCO-08) | `code` unique |
| `occupation_skills` | Required/optional skills per occupation | PK (occupation, skill) |

### Candidates
| Table | Purpose | Key constraints |
|---|---|---|
| `candidates` | PII-free profile used for matching | completeness 0–100; experience ≥ 0; `user_id` unique |
| `candidate_pii` | Identity data, restricted and audited | 1:1 with `candidates`, cascade |
| `candidate_skills` | Skill, level, source and confidence per candidate | PK (candidate, skill); level 1–4; confidence 0–1 |
| `candidate_experiences` | Jobs, including informal work and durations without dates | – |
| `candidate_educations` | Diplomas and training | – |
| `candidate_desired_occupations` | Target occupations, ranked by priority | PK (candidate, occupation) |
| `conversation_sessions` | WP2 dialogues: redacted transcript, intents, interest vector | – |

### Employers, offers, applications
| Table | Purpose | Key constraints |
|---|---|---|
| `employers` | WP4 table plus WP1 columns (`user_id`, `sector_id`, `tax_id`, `governorate_code`, `website`, `description`, `updated_at`) | email unique; `tax_id` unique |
| `job_offers` | Normalized offers (employer form, ministry feed, import) | positions ≥ 1; salary min ≤ max |
| `job_offer_skills` | Required/preferred skills with a minimum level | PK (offer, skill); level 1–4 |
| `applications` | 1-click applications with a score snapshot | unique (candidate, offer) |
| `hiring_feedback` | Employer decision and match quality rating | quality 1–5 |

### Matching
| Table | Purpose | Key constraints |
|---|---|---|
| `match_results` | Global score and the 4 sub-scores, weights used, model version | scores 0–100; unique (candidate, offer, model_version) |
| `skill_gaps` | Missing or insufficient skills for one match | unique (match, skill) |
| `roadmaps` | Learning plan toward an offer or an occupation | a target is required; progress 0–100 |
| `roadmap_items` | Ordered steps (skill → course) | unique (roadmap, position) |

### Training & market
| Table | Purpose | Key constraints |
|---|---|---|
| `training_providers` | Training organizations | – |
| `training_courses` | Course catalog | – |
| `training_course_skills` | Skills taught by a course, with target level | PK (course, skill); level 1–4 |
| `candidate_certifications` | Certification history ("Historique Acquis"), with verification status | – |
| `market_datasets` | One ministry upload (origin, publisher, period) | period_start ≤ period_end |
| `market_indicators` | Normalized indicator rows by occupation/skill/sector/governorate/period | – |

### Platform
| Table | Purpose | Key constraints |
|---|---|---|
| `documents` | Metadata of raw files in storage, plus redacted text and NER output | indexed `sha256` |
| `ingestion_jobs` | One row per ingestion run | – |
| `embeddings` | pgvector store for all entity kinds | unique (entity_type, entity_id, model); HNSW cosine index |
| `audit_logs` | Security-relevant actions | – |

## Enum reference

| Type | Values |
|---|---|
| `user_role` | candidate, employer, admin, ministry, training_provider |
| `onboarding_path` | cv_upload, derja_guided_voice, derja_detailed |
| `literacy_level` | non_literate, basic, literate |
| `education_level` | none, primary, lower_secondary, baccalaureate, vocational_cap, vocational_btp, vocational_bts, licence, master, engineer, doctorate |
| `skill_type` | hard, soft, language |
| `taxonomy_status` | draft, validated, deprecated |
| `skill_relation_type` | broader, related, equivalent |
| `suggestion_status` | pending, approved, rejected, merged |
| `skill_source` | cv, dialogue, certification, self_declared, employer_feedback |
| `requirement_level` | required, preferred |
| `company_size` | 1-10, 11-50, 51-200, 200+ |
| `contract_type` | cdi, cdd, sivp, karama, internship, freelance, seasonal, daily_work |
| `work_mode` | on_site, remote, hybrid |
| `offer_status` | draft, pending_review, published, closed, filled |
| `offer_source` | employer_form, ministry_feed, bulk_import |
| `application_status` | submitted, viewed, shortlisted, interview, offer_made, hired, rejected, withdrawn |
| `hiring_decision` | hired, shortlisted, rejected, no_show |
| `gap_type` | missing, insufficient_level |
| `roadmap_status` | active, completed, abandoned |
| `roadmap_item_status` | todo, in_progress, done, skipped |
| `course_modality` | in_person, online, blended |
| `verification_status` | pending, verified, rejected |
| `market_data_origin` | official, informal, study |
| `market_indicator_type` | job_demand, job_supply, vacancies, unemployment_rate, median_salary, skill_demand |
| `conversation_channel` | text, audio |
| `document_type` | cv, audio, transcript, certificate, market_dataset, training_catalog, other |
| `processing_status` | pending, processing, completed, failed |
| `ingestion_source` | cv_upload, conversation, employer_offer, ministry_market, training_catalog |
| `embedding_entity` | candidate, job_offer, skill, occupation, training_course |

## JSON contracts ↔ tables

| Contract (`contracts/*.schema.json`) | Producer → consumers | Persisted in |
|---|---|---|
| `candidate_profile` | WP2 → WP1 → WP3, WP4, WP6 | `candidates`, `candidate_skills`, `candidate_experiences`, `candidate_educations`, `candidate_desired_occupations` (+ `raw_profile`) |
| `candidate_identity` | WP2 → WP1 → WP6, WP4 after application | `candidate_pii` |
| `appetence_vector` | WP1 → WP2, WP3 | `conversation_sessions.appetence`, `detected_intents` |
| `job_offer` | WP4 → WP1 → WP3, WP6 | `job_offers`, `job_offer_skills` |
| `match_result`, `ranked_matches` | WP3 → WP1 → WP4, WP6 | `match_results`, `skill_gaps` |
| `roadmap` | WP3 → WP1 → WP6 | `roadmaps`, `roadmap_items` |
| `application_create`, `application` | WP6 → WP1 → WP4 | `applications` |
| `hiring_feedback` | WP4 → WP1 → WP3, WP5 | `hiring_feedback` |
| `skill`, `occupation`, `skill_resolve_*`, `skill_suggestion*` | WP1 ↔ all, WP5 review | taxonomy tables |
| `market_dataset`, `market_indicator` | WP5 → WP1 → WP5, WP3 | `market_datasets`, `market_indicators` |
| `skill_gap_aggregate` | WP1 → WP5 | computed from `job_offer_skills` + `candidate_skills` |
| `training_course`, `certification` | Providers → WP1 → WP3, WP6 | `training_*`, `candidate_certifications` |
| `api_error` | all | – |

Contracts use taxonomy **codes** (`skill_code`, `occupation_code`), while tables use UUID foreign keys. WP1 translates between them at the API boundary, so other modules never deal with internal IDs for reference data.

Example payloads: [`contracts/examples/`](../contracts/examples/).
