# WP1 — Data Layer & Preprocessing · Product Requirements Document

| | |
|---|---|
| **Project** | Mahara Match — National Employment Platform (Tunisia) |
| **Work package** | WP1 — Transversal Data Layer & Preprocessing |
| **Owner** | Lead Data (1st) · Co-pilot (2nd) |
| **Status** | Draft v0.1 — S1 deliverable |
| **Date** | September 2026 |
| **Related docs** | [Detailed architecture](ARCHITECTURE.md) · [Architecture summary](ARCHITECTURE_SUMMARY.md) · [Data model](DATA_MODEL.md) |

---

## 1. Context

The platform connects every Tunisian job seeker (graduates with a CV, people without a CV, literate or not, speaking Derja) with employers and with the Ministry of Employment. It is split into six work packages. WP1 is the only one with no user interface. It is the shared foundation the other five read from and write to:

| WP | Module | What it needs from WP1 |
|---|---|---|
| WP2 | Onboarding Agent | Skills taxonomy for structuring; storage for CVs, transcripts and profiles |
| WP3 | Skill Matching Engine | Normalized profiles and offers, vectors, a place to write scores, gaps and roadmaps |
| WP4 | Employer Module | Offer schema, occupation referential, ranked candidates, a sink for hiring feedback |
| WP5 | Admin & Ministry | Taxonomy governance, market-data ingestion, logs and skill-gap aggregates |
| WP6 | Employee Module | Candidate profile, ranked offers, applications, roadmap progress, certifications |

Without a shared layer, each module would define its own "candidate", "skill" and "offer". Scores would then not be comparable, the Ministry dashboards could not aggregate anything, and the same PII would be copied into five places.

## 2. Problem statement

> The platform receives heterogeneous, multilingual and partly unstructured data (PDF CVs, Derja voice transcripts, free-text offers, ministry spreadsheets, training catalogs). The five application modules need that data **clean, PII-safe, mapped to one skills vocabulary, and available through stable contracts**.

## 3. Goals and non-goals

### Goals
- **G1 — One schema.** A single relational + vector schema that all modules share (contract Art. 2).
- **G2 — One vocabulary.** A skills ontology (hard, soft and language skills) and an occupation referential aligned with the Tunisian labour market, including Arabic and Derja labels.
- **G3 — Clean inputs.** A preprocessing pipeline that parses, runs OCR, redacts PII, normalizes and extracts entities (NER) for all five data sources.
- **G4 — Stable contracts.** Versioned JSON contracts and internal REST APIs so each WP can build in parallel against fixed payloads.
- **G5 — Privacy by design.** Personal data is kept apart from matching data, access is role-based, and access to personal data is audited.

### Non-goals (owned elsewhere)
- Conversational UX, Derja fine-tuning and question trees → **WP2**
- Scoring formula, ranking and roadmap generation logic → **WP3** (WP1 only stores the results)
- Employer, admin and candidate user interfaces → **WP4 / WP5 / WP6**
- RBAC role definitions for the admin/ministry views → **WP5** (WP1 enforces them at the data level)

## 4. Users and consumers

| Consumer | Type | Primary interactions |
|---|---|---|
| WP2–WP6 backend services | Machine | Read/write through internal APIs and the shared Python package `mahara_data` |
| Platform admin | Human (via WP5) | Reviews skill suggestions, validates taxonomy versions, monitors ingestion jobs |
| Ministry analyst | Human (via WP5) | Uploads market datasets, consumes skill-gap aggregates |
| Training providers | Human / feed | Publish course catalogs and certifications |

## 5. Functional requirements

Priorities: **M** = Must (MVP, 1 month), **S** = Should, **C** = Could.

### 5.1 Multi-source ingestion
| ID | Requirement | Prio |
|---|---|---|
| FR-ING-01 | Accept CV uploads as PDF, DOCX, JPG and PNG (≤ 10 MB). Store the raw file in object storage and record a `documents` row with a SHA-256 hash. | M |
| FR-ING-02 | Accept conversation transcripts (text, or audio with a transcript) from WP2, linked to a `conversation_sessions` row. | M |
| FR-ING-03 | Accept employer offers from WP4 forms as `NormalizedJobOffer` payloads. | M |
| FR-ING-04 | Accept ministry market data as CSV, Excel or JSON, tagged by origin (official / informal / study) and period. | M |
| FR-ING-05 | Accept training catalogs and certifications as CSV or JSON. | S |
| FR-ING-06 | Track every ingestion run in `ingestion_jobs` (status, record counts, errors, pipeline version). | M |
| FR-ING-07 | Deduplicate uploads by SHA-256 hash; re-uploading the same CV must not create a second profile. | S |

### 5.2 Preprocessing pipeline
| ID | Requirement | Prio |
|---|---|---|
| FR-PRE-01 | Extract text from PDF and DOCX; fall back to OCR (Arabic + French) for scans and images. | M |
| FR-PRE-02 | Detect language and script: Arabic, French, English, Derja in Arabic script, and Derja in Latin script ("Arabizi", e.g. `3` for ع). | M |
| FR-PRE-03 | Redact PII (names, phone numbers including `+216`, emails, national ID-like numbers, addresses) **before** any text is stored for reuse or sent to a model. | M |
| FR-PRE-04 | Normalize syntax: Unicode NFC, Arabic letter normalization (أ/إ/آ → ا, ة/ه, ى/ي), whitespace, casing, date and duration formats. | M |
| FR-PRE-05 | Extract entities (NER): skills, job titles, employers, institutions, diploma levels, durations and locations. | M |
| FR-PRE-06 | Link extracted skills and job titles to taxonomy codes. Unknown labels become `skill_suggestions` instead of being dropped. | M |
| FR-PRE-07 | Classify conversation intents and produce an interest vector over occupations and sectors ("vecteur d'appétence"). | S |
| FR-PRE-08 | Structure offer requirements into skills with a required/preferred flag and a minimum level. | M |
| FR-PRE-09 | Align ministry nomenclatures with the platform's occupation, sector and governorate codes. | M |
| FR-PRE-10 | Validate training equivalences and update the candidate's certification history ("Historique Acquis"). | S |

### 5.3 Skills taxonomy and ontology
| ID | Requirement | Prio |
|---|---|---|
| FR-TAX-01 | Store skills with a stable code, French/Arabic/Derja labels, synonyms, a type (hard/soft/language), a category and a status (draft/validated/deprecated). | M |
| FR-TAX-02 | Store relations between skills (broader / related / equivalent). | M |
| FR-TAX-03 | Store occupations with a national code and an ISCO-08 code, and link them to skills (essential/optional). | M |
| FR-TAX-04 | Resolve a free-text label to the top-k taxonomy codes with a similarity score (`POST /taxonomy/resolve`). | M |
| FR-TAX-05 | Provide a suggestion workflow: suggestions are deduplicated by normalized label and counted; an admin approves, rejects or merges them (WP5). | M |
| FR-TAX-06 | Version skills; deprecated skills stay readable so historical profiles still resolve. | S |
| FR-TAX-07 | Seed the taxonomy with at least 300 skills and 100 occupations covering the priority sectors (IT, construction, agriculture, tourism, textile, services). | M |
| FR-TAX-08 | Optionally map skills to ESCO URIs for interoperability. | C |

### 5.4 Shared database
| ID | Requirement | Prio |
|---|---|---|
| FR-DB-01 | Provide one Postgres schema covering reference data, accounts, taxonomy, candidates, employers/offers, applications, matching, training, market data, documents, embeddings and audit. See [DATA_MODEL.md](DATA_MODEL.md). | M |
| FR-DB-02 | Keep candidate PII in `candidate_pii`, separate from the profile used for matching. | M |
| FR-DB-03 | Store vectors in pgvector, one row per (entity, model), with an HNSW cosine index. | M |
| FR-DB-04 | Snapshot the match score at application time so later re-scoring does not rewrite history. | M |
| FR-DB-05 | Support soft deletion and erasure of a candidate (cascade to PII, skills, documents and matches). | M |
| FR-DB-06 | Ship all schema changes as versioned SQL migrations under `supabase/migrations/`. | M |

### 5.5 Internal APIs and contracts
| ID | Requirement | Prio |
|---|---|---|
| FR-API-01 | Publish JSON Schemas for every inter-WP payload under `data-layer-wp1/contracts/`, generated from the Pydantic models. | M |
| FR-API-02 | Expose internal REST endpoints (`/internal/v1/...`) for profiles, offers, taxonomy, matches, applications, feedback, market data and training. See [ARCHITECTURE.md §7](ARCHITECTURE.md#7-internal-api-catalog). | M |
| FR-API-03 | Publish the shared Python package `mahara_data` (ORM + contracts) that Python WPs can import instead of copying models. | M |
| FR-API-04 | Put a `schema_version` in every contract. Breaking changes bump the major version and keep the previous version for one sprint. | M |
| FR-API-05 | Return errors in one shape (`ApiError`: code, message, details). | M |
| FR-API-06 | Provide a gRPC endpoint for bulk scoring reads by WP3. | C |

### 5.6 Governance, security and observability
| ID | Requirement | Prio |
|---|---|---|
| FR-SEC-01 | Enforce RBAC at the data layer for the roles candidate, employer, admin, ministry and training_provider. | M |
| FR-SEC-02 | Enable Row Level Security (deny-by-default) on every table exposed through Supabase. | M |
| FR-SEC-03 | Write every read of `candidate_pii` and every taxonomy validation to `audit_logs`. | M |
| FR-SEC-04 | Record consent (version and timestamp) before a candidate profile is stored. | M |
| FR-OBS-01 | Expose ingestion metrics (volume, error rate, latency per source) for the WP5 monitoring dashboard. | S |
| FR-OBS-02 | Feed hiring feedback back to WP3 (retraining signal) and WP5 (impact reports). | M |

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| **Privacy & compliance** | Comply with Tunisian personal data law (Organic Law No. 2004-63) and INPDP guidance: purpose limitation, consent, right of access and erasure, data minimization. No national ID number is collected. |
| **Bias** | Gender, age, origin and name never reach the matching engine. They live only in `candidate_pii`. |
| **Sovereignty** | All data and models are hosted locally; no raw CV or transcript is sent to a third-party API (contract Art. 4). |
| **Languages** | Full UTF-8 with Arabic RTL text. Labels in FR and AR, plus Derja where relevant. |
| **Performance (MVP)** | Internal read APIs p95 < 300 ms. CV end-to-end processing < 60 s. Top-50 vector search < 200 ms at 100k vectors. |
| **Scalability (target)** | 1M candidates, 100k active offers, 10M match results without a schema change. |
| **Reliability** | Ingestion is idempotent and can be retried. A failed record does not fail the whole batch. |
| **Traceability** | Every derived record can be traced back to its source document or conversation and to the pipeline/model version that produced it. |
| **Maintainability** | ORM, SQL migration and JSON contracts are checked for consistency in CI (`tests/test_migration_sync.py`). |

## 7. Data sources (ingestion matrix)

| Source | Raw format | Processing | Output → consumers |
|---|---|---|---|
| Uploaded CVs | PDF, DOCX, images | Parsing, OCR, PII redaction, NER | `CandidateProfile` JSON → WP3, WP6 |
| Conversations | Text, transcripts | Syntax cleanup, intent classification | `AppetenceVector` → WP2, WP3 |
| Employer offers | Web forms, free text | Requirement structuring, job-title normalization | `NormalizedJobOffer` → WP4, WP3 |
| Market data (Ministry) | CSV, Excel, JSON feeds | Metadata standardization, nomenclature alignment | Occupation referential + `MarketIndicatorRecord` → WP5, WP3 |
| Training providers | CSV/JSON certifications | Equivalence validation, certification history update | `TrainingCourseRecord`, `CertificationRecord` → WP6, WP5 |

## 8. Deliverables and milestones

| Step | Week | Deliverable | Acceptance criteria |
|---|---|---|---|
| 1 | W1 | **DB schema & API contracts** *(S1 commitment)* | Migration applies on a clean Supabase project; JSON Schemas published; WP2–WP6 leads have reviewed the contracts |
| 2 | W2 | Skills taxonomy v1 | ≥ 300 skills / 100 occupations seeded; resolve endpoint top-3 accuracy ≥ 80% on a 100-label test set |
| 3 | W2–3 | Ingestion connectors | Upload, webhook and batch import work for all 5 sources; each run is visible in `ingestion_jobs` |
| 4 | W3 | Preprocessing & NER | PII recall ≥ 95% on the annotated set; skill extraction F1 ≥ 0.75 on 50 annotated CVs |
| 5 | W4 | Shared DB & internal APIs deployed | All endpoints in §7 of the architecture live, with OpenAPI docs |
| 6 | W4 | Integration testing | End-to-end run: CV → profile → match → application → feedback, across the 5 modules |

## 9. Success metrics

- **Adoption:** all 5 modules read and write through WP1 contracts; no module keeps its own copy of candidate or offer tables.
- **Coverage:** ≥ 90% of extracted skills are linked to a taxonomy code (the rest go to suggestions).
- **Quality:** PII leaks = 0 in the matching payloads (automated check on the `CandidateProfile` schema plus a redaction audit sample).
- **Freshness:** a new offer is searchable by WP3 in < 5 min after publication.

## 10. Dependencies

| Direction | WP | Item |
|---|---|---|
| Inbound | WP2 | Profile JSON, transcripts, raw CV uploads |
| Inbound | WP4 | Offers, hiring feedback |
| Inbound | WP5 | Market datasets, taxonomy decisions, RBAC role matrix |
| Inbound | Training providers | Catalogs, certifications |
| Outbound | WP3 | Profiles, offers, taxonomy, vectors; receives scores, gaps, roadmaps |
| Outbound | WP5 | Logs, ingestion metrics, skill-gap aggregates, feedback |
| Outbound | WP6 | Profile, ranked offers, applications, roadmaps, certifications |

## 11. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Derja has no standard spelling (Arabic vs Latin script, regional variants) | Low skill-linking recall | Derja and Arabizi synonyms in `alt_labels`, semantic resolve via embeddings, suggestion loop fed by real transcripts |
| Low-quality scans and phone photos of CVs | OCR errors | Image preprocessing (deskew, binarization), confidence score per extracted skill, WP2 confirms skills with the candidate |
| Ministry nomenclatures differ from the platform's codes | Wrong aggregates | Explicit mapping tables built during ingestion; unmapped rows reported in `ingestion_jobs.errors` |
| Modules drift from the contracts | Integration failures in W4 | Shared package + JSON Schemas + sync tests in CI; contract review in W1 |
| PII leaking into logs or vectors | Legal and trust risk | Redaction before persistence/embedding; PII in a separate table; audit log; no PII in `raw_profile` |
| WP4 already created its own `employers` table | Schema conflict | WP1 migration is idempotent and extends WP4's table without changing its columns (see ARCHITECTURE §11) |

## 12. Open questions

1. **Occupation nomenclature:** which national code list does the Ministry use today? The schema supports a national code and ISCO-08; the choice decides the seed.
2. **Account model:** employers currently authenticate through their own `employers.password_hash` (WP4). Should all roles move to the shared `users` table? The schema supports both through `employers.user_id`.
3. **Embedding model:** confirm the 768-dimension multilingual model with WP3 (candidates: `intfloat/multilingual-e5-base`, `paraphrase-multilingual-mpnet-base-v2`). WP3's PoC uses ChromaDB; the shared store is pgvector.
4. **Retention:** how long are raw CVs and audio kept after profile extraction? Proposed: 12 months, then deleted, keeping only the redacted text.
