"""Regenerate contracts/*.schema.json from the Pydantic contracts.

Run from data-layer-wp1/:  python -m scripts.export_json_schemas
"""

import json
from pathlib import Path

from mahara_data.schemas import PUBLISHED_CONTRACTS

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"


def render(model) -> str:
    return json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    CONTRACTS_DIR.mkdir(exist_ok=True)
    for name, model in PUBLISHED_CONTRACTS.items():
        (CONTRACTS_DIR / f"{name}.schema.json").write_text(render(model), encoding="utf-8")
    print(f"Wrote {len(PUBLISHED_CONTRACTS)} schemas to {CONTRACTS_DIR}")


if __name__ == "__main__":
    main()
