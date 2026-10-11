from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "offre.txt"


def generer_offre_ecrite(answers: dict[str, str]) -> str:
    valeurs = {
        "metier": answers.get("metier"),
        "date": answers.get("date_disponibilite"),
        "gouvernorat": answers.get("gouvernorat"),
        "telephone": answers.get("telephone"),
    }
    valeurs_formatees = {
        champ: (valeur or "").strip() or "ما تحددش"
        for champ, valeur in valeurs.items()
    }
    return TEMPLATE_PATH.read_text(encoding="utf-8").format(**valeurs_formatees)
