# Candidate–Job Matching: Audit and Design

## Scope and recommendation

This document records the repository audit and the incremental design. The
implementation status below describes the first delivered slice; the rest of
the roadmap remains proposed work.

**Recommendation:** retain PostgreSQL and model the first knowledge graph as
small, curated relational tables connected to the existing skill catalogue,
candidate profiles, offers, and courses. Add multilingual semantic similarity
as a low-weight, separately reported signal after building an evaluation set.
Do not add Neo4j, a new vector database, or an LLM for the initial release.
Preserve `GET /candidate/matches` and its existing response fields while adding
optional explanations and score details.

## 1. Existing-system audit

### Current matching behavior

At audit time, `candidate_matches` in
[`backend/app/main.py`](../backend/app/main.py) loaded the current candidate
profile and all published job offers, ordered newest first. It built a
case-folded lookup from `CandidateProfile.skills`, checked every offer's
`required_skills` against that lookup, and returned all published offers
without ranking them by match score.

The score is rounded to an integer percentage:

```text
match_score = round(100 * number_of_exact_required_skill_matches
                        / number_of_required_skills)
```

In the implementation, rounding is performed by adding `0.5` before converting
to `int`. `matched_skills` contains exact matches, and `missing_skills` contains
the remaining requirements. Preferred skills, experience, job title, and
description do not affect the score. The endpoint requires the candidate's
own-match permission and records a sensitive-read audit event. The existing
test asserts a 50% result for one exact match out of two requirements in
[`backend/tests/test_matching_offers.py`](../backend/tests/test_matching_offers.py).

The endpoint assumes each offer has at least one required skill. New offer
requests enforce that, but the scoring code has no explicit zero-requirement
guard for legacy or manually modified records. The migration plan should define
the result for such records before introducing the new scorer.

### Available data and normalization

| Area | Current representation | Matching relevance |
|---|---|---|
| Candidate skills | `CandidateProfile.skills` JSON list; aliases are canonicalized on profile update | Used by the endpoint for exact string matching |
| Normalized candidate skills | `candidate_skills` links to `skills_catalogue` | Exists but is not queried by the endpoint |
| Offer requirements | `JobOffer.required_skills` JSON list | Used for the denominator and exact matching |
| Preferred skills | `JobOffer.preferred_skills` JSON list and `offer_skills` links with a `skill_type` | Persisted but ignored by the endpoint |
| Skill catalogue | French and English canonical names plus aliases in `skills_catalogue`; seed data in `backend/data/skills_catalogue.json` | Supports canonicalization, not skill-to-skill inference |
| Unrecognized skills | `skill_alias_review` queue | Enables catalogue maintenance |
| Candidate occupations/experience | `professional_headline`, legacy `experience` text, and structured `experience_entries` with job title and responsibilities | Available, but not used in matching |
| Offer occupation/responsibilities | `JobOffer.title` and free-text `description` | No structured occupation or responsibility fields |
| Training | Courses and `course_skills` links | Could later support skill-to-training relationships |
| Semantic vectors | `knowledge_chunks` has 1024-dimension pgvector embeddings and model metadata | Used for knowledge retrieval only, not profiles or offers |

`sync_candidate_skills`, `sync_offer_skills`, and
`canonicalize_skills` in [`backend/app/skill_catalog.py`](../backend/app/skill_catalog.py)
maintain canonical names and normalized link rows. Those link tables are useful
foundations for graph edges, but they currently store no relationship between
different skills. The normalizer's character allowlist is Latin-oriented; it
does not preserve Arabic letters. Add Unicode and Arabic normalization tests
before relying on it for multilingual canonicalization.

The candidate profile and offer schemas are in
[`backend/app/schemas.py`](../backend/app/schemas.py). The frontend's
`JobMatch` type and card in [`src/auth.ts`](../src/auth.ts) and
[`src/workspaces.tsx`](../src/workspaces.tsx) consume `match_score`,
`matched_skills`, and `missing_skills`. The UI currently describes the score as
only comparing declared skills and uses a 60% badge threshold. Any changed
meaning must update that copy and the display together.

### Existing foundations and gaps

Reusable foundations:

- SQLAlchemy models, PostgreSQL, Alembic migrations, and SQLite-backed pytest
  fixtures.
- The skill catalogue, aliases, normalized link tables, and review queue.
- Structured experience responsibilities and job descriptions.
- An existing OpenAI-compatible embedding service and pgvector storage in
  `backend/app/knowledge_base.py`. Embedding calls are optional/configured by
  environment; current persistence and retrieval are scoped to knowledge
  documents and chunks.
- Existing candidate-match response types, UI, access controls, and audit
  logging.

Gaps to address:

- No graph relationships, occupation taxonomy, structured offer
  responsibilities, or provenance/confidence for inferred relationships.
- No matching-specific embedding lifecycle, similarity index, calibration, or
  evaluation dataset.
- The route uses profile JSON rather than normalized skill links and performs
  exact string matching only.
- Requirements are only split into required and preferred lists; there is no
  explicit per-requirement mandatory flag, proficiency, or experience level.
- Existing matching explanations identify direct/missing skills only.

## 2. Knowledge-graph design

### Keep the graph small and grounded

Do not create duplicate Candidate or Job Offer graph nodes. The existing
`candidate_profiles`, `job_offers`, and course rows remain the authoritative
entities; their foreign keys are the graph's links to those entities.

Start with:

1. **Skill** — reuse `skills_catalogue`.
2. **Occupation** — a curated occupation record with localized names and
   aliases.
3. **Responsibility** — a reusable, localized responsibility/task concept.
4. **Existing candidate experience, offer, and course records** — linked to
   those concepts through relation tables.

Treat competency as a skill-family/category or a typed responsibility at first,
rather than introducing a second overlapping concept hierarchy. Treat industry
as an optional tag until evaluation shows it improves ranking. Training is
already represented by course records; model its edges only when the course
skill links need richer provenance.

Suggested relational implementation:

- `skill_relationships(from_skill_id, to_skill_id, relation_type, strength,
  confidence, source, reviewed_at)`, unique on endpoints and type.
- `occupations(id, canonical_name_fr, canonical_name_en, aliases)`.
- `responsibilities(id, canonical_name_fr, canonical_name_en, aliases)`.
- Typed join tables for occupation-to-responsibility, occupation-to-skill,
  candidate-experience-to-responsibility, offer-to-responsibility, and
  occupation-to-offer. Include source, confidence, and review state on
  inferred or curated links.
- Add indexes on both endpoint columns, relation type, and entity foreign keys.

Keep the initial vocabulary curated and versioned. Do not silently turn an
embedding-near skill into an equivalence edge. Graph expansion should be
bounded (initially one hop for skill links and one mapping through an
occupation/responsibility), use only approved edge types, and retain the path
for explanation.

### Edges and matching semantics

Strength and confidence are each in `[0, 1]`. Strength expresses how useful
the relation is for transfer; confidence expresses the evidence quality. Store
the source/provenance separately so a reviewer can see why an edge exists.
Relations with no reviewed evidence should not contribute to a production
score.

| Edge | Direction | Meaning and example | Matching contribution |
|---|---|---|---|
| `FOUNDATION_OF` | Directional | SQL fundamentals → advanced data warehousing | Partial evidence for the target; never equivalent to the target skill |
| `RELATED_TO` | Semantically symmetric; store a canonical pair or reciprocal rows consistently | PostgreSQL ↔ relational database administration | Partial transfer when the candidate skill and required skill are connected by an approved edge |
| `USED_WITH` | Symmetric association | Python ↔ data visualization | Context only; does not satisfy either requirement on its own |
| `REQUIRED_FOR` | Skill → responsibility or occupation | Data analysis → analyze operational data | Supports occupation/responsibility coverage |
| `INVOLVES` | Occupation → responsibility | Data analyst → clean and interpret datasets | Maps experience to target role evidence |
| `PERFORMS` | Candidate experience → responsibility | Experience entry → prepare monthly reports | Supports transferable responsibility evidence only when the profile text or a reviewed mapping supports it |
| `REQUIRES` | Offer → skill/competency | Offer → Python (required) | Represents the requirement; direct evidence is strongest |
| `DEVELOPS` | Course → skill/competency | Course → Excel reporting | Potential roadmap/explanation context; not proof that the candidate already has the skill |

Example path:

```text
Candidate skill: Python
  --RELATED_TO (reviewed, strength 0.55)--> Data processing
  --REQUIRED_FOR--> Data analysis responsibility
  --INVOLVES--> Data Analyst occupation
  <--target offer occupation
```

The candidate's explicit Python skill may support a partial related-skill or
responsibility signal. It must not be reported as a direct Data Analysis match.
If the candidate also explicitly describes cleaning and analyzing datasets,
that experience is separate, attributable responsibility evidence.

### Storage options

| Option | Complexity / maintenance | Query characteristics | Fit here |
|---|---|---|---|
| Relational relationship tables | Low; uses current SQLAlchemy/Alembic stack | Predictable indexed one-hop joins; adequate for a curated shallow graph | **Recommended** |
| Neo4j or another graph database | New service, deployment, backup, access-control, and synchronization burden | Convenient for deep, exploratory traversals | Not justified until multi-hop graph queries become a measured bottleneck |
| PostgreSQL plus a graph database | Highest consistency and operational burden | Supports specialized graph/vector workloads | Defer; duplicates authoritative data and adds synchronization failure modes |

PostgreSQL already supports the required joins and pgvector. A normalized
relational graph is the simplest maintainable choice for this bounded domain.
Revisit a dedicated graph store only if measured query patterns require deep
multi-hop traversal that SQL cannot serve within the response-time target.

## 3. Semantic matching

### Recommended approach

Use a multilingual sentence-embedding model behind the existing embedding
service contract, initially in shadow evaluation. Compare at least:

- The currently configured BGE-M3-compatible embedding model, if the deployed
  service provides it with the existing 1024-dimensional schema.
- A multilingual Sentence Transformers candidate such as
  `paraphrase-multilingual-mpnet-base-v2`, measured on the project's French,
  Modern Standard Arabic, Tunisian Arabic/Derja, and English examples.

Treat model names as candidates, not a guarantee of quality: compare cross
language retrieval and job-domain relevance on a human-labeled dataset. The
current knowledge-base BGE-M3 setting is an integration point, not evidence
that its current index or configuration is already suitable for matching.
Do not reuse `knowledge_chunks` as a profile/offer store.

Build separate text views for:

- Candidate headline and each structured experience's title and
  responsibilities.
- Offer title and description, plus structured responsibilities when added.

Keep skill names as structured signals; do not let an embedding replace skill
coverage. Compare candidate experience segments to offer responsibility
segments and take a calibrated best evidence score rather than summing similar
segments. Store each embedding's model/version, dimensions, language (when
known), source-text hash, and update time. Re-embed when source text or model
version changes.

For an initial small catalogue, calculate pairwise cosine similarity for
published offers after fetching them in one query. Before scaling, benchmark
this path and then persist profile/offer embeddings and use PostgreSQL pgvector
with metadata filters and an HNSW index. Avoid a new vector database unless
PostgreSQL is shown to miss the latency or capacity target.

The present embedding client is optional and calls an OpenAI-compatible
service; therefore, no new model package or external provider is required for
the first matching release. If local inference is later preferred, benchmark
its memory, latency, operating cost, and Arabic/Derja quality before adding a
Sentence Transformers runtime dependency. An LLM is not needed: embeddings,
curated edges, and deterministic scoring provide more stable and inspectable
signals.

## 4. Hybrid scoring and ranking

### Per-requirement evidence

For every distinct required skill, select **one best evidence item** from the
candidate profile:

```text
direct canonical match                 = 1.00
approved RELATED_TO transfer           = at most 0.55
approved FOUNDATIONAL_OF transfer       = at most 0.35
no supported evidence                  = 0.00
```

For an inferred edge, multiply its relation cap by edge strength and
confidence. Do not sum multiple paths or multiple candidate skills for the same
requirement. Keep direct, related, and foundational coverage in separate
components. Candidate skills outside the curated graph remain eligible for
exact matching after canonicalization but generate no inferred credit.

### Initial configurable weights

All components are percentages in `[0, 100]`. Start with conservative weights
and tune them only against held-out labeled data:

These are proposed target weights for a later full hybrid scorer, not the
weights used by the implemented first slice below.

```text
score = 0.65 * direct_required
      + 0.15 * related_required
      + 0.05 * foundational_required
      + 0.05 * preferred_skill_coverage
      + 0.08 * responsibility_similarity
      + 0.02 * occupation_similarity
      + 0.00 * semantic_description_similarity   # shadow-only at launch
```

After the semantic signal demonstrates an offline gain without an unacceptable
false-positive increase, enable it by transferring at most 0.03 from
responsibility/occupation weights; keep direct required-skill evidence at
0.65. For example, a later configuration may use `0.06` for responsibilities,
`0.01` for occupation, and `0.03` for semantic similarity. Store the active
weights and scoring version in configuration and include the version in the
response. Do not normalize away missing weights or silently change defaults.

The denominator for each coverage component is the number of applicable,
distinct requirements; an empty component is explicitly `null` and excluded
from the weighted average, not treated as 100%. For historical offers with no
required skills, return a documented no-requirements state and no misleading
percentage until the offer is corrected.

Current `required_skills` should continue to mean required for compatibility.
Add an explicit `mandatory`/`preferred` distinction only through a
backward-compatible schema migration and employer UX. A semantic score must
not satisfy a mandatory skill. Rank candidates lexicographically by
mandatory-direct coverage first, then total hybrid score, then stable offer
recency/ID ordering. Report missing mandatory items and direct coverage even
when other signals raise the total. Do not automatically make a hiring
decision; this remains a recommendation.

### Safeguards against false positives and double-counting

- Canonicalize aliases before scoring; do not use fuzzy string similarity as
  equivalence.
- Restrict relationship traversal to reviewed types and bounded paths.
- Use the maximum contribution per required skill, not the sum over paths.
- Cap all inferred required-skill credit separately from direct coverage.
- Keep preferred coverage separate and lower weighted than required coverage.
- Keep responsibility and occupation similarity bounded and report them as
  inferred evidence.
- Give semantic similarity a small maximum weight; it cannot erase a mandatory
  gap or create a direct skill match.
- Do not infer skill proficiency or years of experience from an embedding.
- Treat missing profile fields as unknown, not as evidence of poor fit.
- Version and calibrate weights; audit score distributions and inspect
  false-positive examples before changing thresholds.

### Implemented first slice

The initial implementation adds a `skill_relationships` table with bounded
strength/confidence fields and four seeded skill edges. Exact canonical matches
remain worth `1.0`. Related edges contribute at most `0.55 * confidence`;
foundational edges contribute at most `0.35 * confidence`. For each required
skill, the scorer selects one best item of evidence, and the offer score is the
rounded average of those per-requirement contributions. Empty requirements
produce a null score. Preferred skills, occupation/responsibility links, and
semantic similarity do not yet contribute.

`GET /candidate/matches` retains `match_score`, `matched_skills`, and
`missing_skills`, adds versioned score components and structured explanations,
and orders offers first by direct required-skill coverage, then hybrid score;
the original recency ordering remains the stable tie-breaker. The
frontend labels direct and inferred skill evidence separately. The current
caps are centralized in the scorer and can be overridden when calling it; a
future calibration phase should decide whether to expose configuration beyond
the code. Relationship explanations include the stored edge's provenance.

## 5. Explainability and API evolution

Keep the current fields and add fields so older clients can continue to parse
the response. The following is a target shape; the current response contains
the exact and skill-graph fields implemented in this phase:

```json
{
  "id": "offer-id",
  "title": "Data Analyst",
  "match_score": 74,
  "matched_skills": ["Python"],
  "missing_skills": ["Data Analysis"],
  "score_version": "hybrid-v1",
  "score_components": {
    "direct_required": 50,
    "related_required": 0,
    "foundational_required": 0,
    "preferred_skills": null,
    "responsibilities": 82,
    "occupation": null,
    "semantic_description": null,
    "mandatory_direct_coverage": 50
  },
  "explanations": [
    {
      "kind": "direct_skill",
      "requirement": "Python",
      "evidence": "Python",
      "contribution": 1.0,
      "source": "candidate_profile.skills"
    },
    {
      "kind": "transferable_responsibility",
      "requirement": "Analyze operational data",
      "evidence": "Prepared monthly reports from sales data",
      "contribution": 0.82,
      "source": "candidate_profile.experience_entries[0].responsibilities"
    },
    {
      "kind": "missing_required_skill",
      "requirement": "Data Analysis"
    }
  ]
}
```

Actual responses should use validated Pydantic models and allowlist explanation
`kind` values. Include only the requesting candidate's own evidence on this
candidate endpoint; do not expose one candidate's profile, experience, or
embeddings to another user. Keep private contact/profile fields out of matching
text and explanations. The UI should label direct and inferred evidence
distinctly, explain that the score is advisory, and update its current
skills-only description and threshold semantics.

## 6. Incremental implementation roadmap

| Phase | Objective and modifications | Files / migration / dependency | API and tests / acceptance |
|---|---|---|---|
| 1. Audit and baseline | Record current endpoint behavior, collect a consented/labeled evaluation set, and capture baseline ranking and latency. | This document; `backend/tests/test_matching_offers.py`; no dependency. | Initial implementation retains exact baseline score when all requirements match directly and measures empty requirements explicitly. |
| 2. Data quality and structured inputs | Add explicit offer responsibilities and, if employers can supply them, must-have vs preferred requirement importance. Improve Unicode/Arabic normalization without changing existing canonical IDs. | `backend/app/schemas.py`, `models.py`, `skill_catalog.py`, employer offer UI; Alembic migration for new fields/tables; no dependency. Depends on phase 1. | Keep old offer payloads valid. Add migration/backfill, French/Arabic/English normalization tests, legacy response tests, and tests for unrecognized skills. |
| 3. Curated skill relations | Add reviewed directed/symmetric skill edges with relation type, strength, confidence, and source. Expand the initial curated vocabulary only after review. | `backend/app/matching/`; `models.py`; migration `0034_curated_skill_relationships.py`. No new dependency. | Implemented initial edges and bounded one-hop traversal. Tests cover partial credit, direct-match priority, and max-one-contribution behavior; expand edge-governance tests before broadening the catalogue. |
| 4. Occupation and responsibility model | Add localized occupation/responsibility concepts and curated mappings; connect candidate experience and offers using explicit data or reviewed extraction. | New matching taxonomy/data modules; `schemas.py`, `models.py`, employer/profile UI; Alembic migration. Depends on phase 2. | Initially internal/shadow only. Test locale aliases, mapping provenance, missing-text behavior, and no title-only false equivalence. |
| 5. Embeddings and similarity | Evaluate multilingual models; embed relevant experience and offer text; maintain model/version/hash and refresh behavior. | New `backend/app/matching/embeddings.py`; reuse/extract the embedding client contract from `backend/app/knowledge_base.py`; Alembic vector columns/index only if persistence is justified. No mandatory new dependency. Depends on phase 1 and structured text from phase 2/4. | No response change in shadow mode. Test deterministic cosine calculation, model/dimension mismatch, stale embeddings, failure reporting, timeout, and bounded latency. |
| 6. Hybrid scoring engine | Implement pure deterministic scoring components, configurable relationship caps, mandatory coverage, and score version. | `backend/app/matching/scoring.py`; focused unit tests; no new dependency. Depends on phase 3. | Initial exact + graph skill scoring is implemented. Occupation, responsibility, semantic signals, and evaluation-driven weights remain future work. |
| 7. Endpoint integration | Route published offers through the scorer and reuse canonical skill IDs where available, with explicit handling for unmapped/legacy skills. | `backend/app/main.py`; `backend/app/matching/scoring.py`; migration from phase 3. | Implemented with original fields, own-candidate permission, audit event, score ordering, and endpoint tests. |
| 8. Explanations and frontend | Add validated structured score components/explanations and distinguish direct, related, and foundational evidence in French UI. | `backend/app/schemas.py`, `src/auth.ts`, `src/workspaces.tsx`. | Implemented additively. Responsibility and semantic explanations await those later signals. |
| 9. Offline evaluation and tuning | Compare baseline, graph-only, graph+semantic, and final hybrid on held-out examples; adjust weights only with documented evidence. | Evaluation fixture/tool under `backend/tests/` or a separately governed evaluation dataset; configuration changes only. Depends on phases 1, 3, 5–8. | Measure Precision@K, Recall@K, NDCG@K, MRR, mandatory direct coverage, false-positive rate, latency, and score calibration. Require non-regression for mandatory coverage and agreed false-positive limits before enabling semantic weight. |
| 10. Rollout and monitoring | Shadow, canary, then enable the reviewed scorer; track model errors, latency, distributions, and user feedback. | Feature/config flag and operational docs; no new DB unless telemetry retention needs it. Depends on phase 9. | Roll back by configuration to the exact baseline scorer. Keep backward-compatible endpoint and frontend behavior throughout rollout. |

Suggested module boundaries keep graph lookup, embedding generation, scoring,
and orchestration independently testable. Do not grow `main.py` into the
matching engine.

## 7. Evaluation plan

### Dataset and labeling

Create a small, versioned set of realistic Tunisian-market candidate profiles
and offers, stratified across French, Arabic, Derja, and English text and
occupational domains. Begin with consented/de-identified examples or carefully
constructed synthetic cases, then have at least two domain reviewers judge
candidate-offer relevance independently and resolve disagreements. Synthetic
profiles are useful for edge cases but are not sufficient as the only
ground-truth source.

Use relevance labels such as `0 = not relevant`, `1 = weak/unsupported`,
`2 = relevant`, and `3 = strong`. Split by candidate and offer/template before
tuning to prevent near-duplicate leakage. Keep a challenge set for multilingual
paraphrases, sparse profiles, ambiguous skills, and hard negatives.

Required cases:

1. Identical required skills: exact matching should rank highly and explain
   direct evidence.
2. Related but non-identical skill: receive only bounded, confidence-adjusted
   partial credit and a related-skill explanation.
3. Transferable responsibilities: responsibility overlap contributes without
   falsely claiming a direct skill match.
4. Similar experience with a different title: duties may support relevance;
   title overlap alone should not.
5. Semantically similar description but missing mandatory skills: semantic
   evidence remains visibly small and cannot satisfy the missing requirement.
6. French-to-Arabic/English paraphrase, Arabic-script and Derja examples:
   measure cross-lingual retrieval and normalization explicitly.
7. Unsupported edge, multiple graph paths, empty requirements, and no
   candidate experience: no inflated or success-shaped fallback score.

### Metrics and release criteria

Report metrics at several `K` values (for example 5 and 10):

- **Precision@K** and **Recall@K** for relevant offers.
- **NDCG@K** using graded human relevance.
- **MRR** for the first relevant offer.
- **Mandatory skill coverage** as direct exact coverage, separate from inferred
  coverage.
- **False-positive rate**, especially semantically similar offers that lack
  mandatory skills.
- **Latency** (p50/p95), embedding-service availability, and embedding refresh
  lag.

Compare four frozen versions: baseline exact skill matching; exact plus
approved skill relationships; exact plus graph and semantic similarity; and
the complete hybrid engine. Use the same held-out profiles, offers, and
publication filters for each. Report results by language and profile
completeness as well as overall. Promote a change only when it improves a
pre-agreed ranking metric without violating the mandatory-coverage and
false-positive guardrails. Keep the baseline available for rollback.

## 8. Compatibility, operations, and open decisions

- Continue to return published offers only. Preserve existing response fields
  and endpoint authorization/audit behavior.
- Keep semantic embeddings optional until their multilingual quality and
  operational latency are measured. An embedding outage must not silently
  produce a semantic score of zero that appears as a valid full match; expose
  unavailable components and use a documented baseline/shadow fallback.
- Keep scoring deterministic for a fixed profile, offer, graph revision,
  model version, and weight configuration.
- Add migrations and focused tests for every schema change; current backend
  fixtures use in-memory SQLite, so PostgreSQL-specific vector/index behavior
  also needs a PostgreSQL migration/integration check.
- Agree on the evaluation set, acceptable false-positive ceiling, response
  latency target, whether every existing required skill is a hard mandatory
  requirement, and the embedding deployment/model before enabling semantic
  scoring in production.
