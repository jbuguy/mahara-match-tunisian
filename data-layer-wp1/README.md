# WP1 — Data Layer & Preprocessing

Shared data foundation of Mahara Match: the database schema, the skills taxonomy model, and the JSON contracts that WP2–WP6 exchange.

| Document | Content |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements: goals, functional/non-functional requirements, milestones, risks |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed architecture: components, pipeline, flows, API catalog, security, decisions |
| [docs/ARCHITECTURE_SUMMARY.md](docs/ARCHITECTURE_SUMMARY.md) | One-page summary with the essentials |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | ER diagrams, table catalog, enums, contract ↔ table mapping |

## Layout

```
mahara_data/
  enums.py          shared enums (mirrored as Postgres enum types)
  reference.py      governorates, proficiency scale, embedding dim, scoring weights
  db/models/        SQLAlchemy 2 models, one module per domain
  schemas/          Pydantic v2 contracts, one module per domain
contracts/          generated JSON Schemas + example payloads
scripts/            export_json_schemas.py
tests/              ORM ↔ SQL sync, model and contract tests
../supabase/migrations/20260921000000_wp1_shared_schema.sql
```

## Setup

```bash
cd data-layer-wp1
python -m venv .venv
.venv/Scripts/activate        # Windows  (source .venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
pytest
```

## Using it from another WP

```bash
pip install -e ../data-layer-wp1
```

```python
from mahara_data.schemas import CandidateProfile, MatchResult
from mahara_data.db.models import Candidate, JobOffer

profile = CandidateProfile.model_validate_json(payload)   # rejects unknown fields and invalid codes
```

Teams that don't use Python can validate against `contracts/*.schema.json`.

## Applying the schema

```bash
supabase db push                 # from the repo root, with a linked Supabase project
```

## Changing the schema or a contract

1. Edit the SQL migration (or add a new one) **and** the matching ORM model.
2. If a contract changed, run `python -m scripts.export_json_schemas`.
3. Run `pytest`. The sync tests fail if the SQL, the ORM, the enums or the exported schemas disagree.
