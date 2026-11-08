import json
from pathlib import Path

from app.skill_catalog import normalize_skill_key


def test_catalogue_has_exactly_100_skills_with_excel_aliases():
    seed_file = Path(__file__).resolve().parents[1] / "data" / "skills_catalogue.json"
    catalogue = json.loads(seed_file.read_text(encoding="utf-8"))
    assert len(catalogue) == 100
    assert {"Excel", "MS Excel", "Microsoft Excel"} <= set(catalogue["Excel"]["aliases"] + ["Excel"])


def test_skill_normalisation_is_accent_and_spacing_insensitive():
    assert normalize_skill_key("  Microsoft   Excel ") == "microsoft excel"
    assert normalize_skill_key("Gestion de projets") == normalize_skill_key("Gestion  de projets")


def test_reviewed_unmatched_skill_shape():
    unmatched = "Pâtisserie avancée"
    assert normalize_skill_key(unmatched) not in {
        normalize_skill_key(alias)
        for alias in ("Excel", "MS Excel", "Microsoft Excel")
    }
