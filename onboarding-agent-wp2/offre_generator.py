from pathlib import Path

import csv_store


TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "offre.txt"


def generer_offre_ecrite(session_id):
    session = csv_store.lire_session(session_id, csv_store.CSV_PATH)
    valeurs = {
        "metier": session.get("metier"),
        "date": session.get("date_disponibilite"),
        "gouvernorat": session.get("gouvernorat"),
        "telephone": session.get("telephone"),
    }
    valeurs_formatees = {
        champ: (valeur or "").strip() or "ما تحددش"
        for champ, valeur in valeurs.items()
    }
    return TEMPLATE_PATH.read_text(encoding="utf-8").format(**valeurs_formatees)