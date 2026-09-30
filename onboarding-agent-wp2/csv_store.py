import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

from questions import QUESTIONS


CSV_PATH = Path(__file__).resolve().parent / "sessions.csv"
BASE_COLUMNS = ["session_id", "horodatage"]
QUESTION_COLUMNS = [question["colonne_csv"] for question in QUESTIONS]
CSV_COLUMNS = BASE_COLUMNS + QUESTION_COLUMNS


def _initialiser_csv(chemin_csv):
    chemin = Path(chemin_csv)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    if not chemin.exists() or chemin.stat().st_size == 0:
        with chemin.open("w", newline="", encoding="utf-8") as fichier:
            csv.DictWriter(fichier, fieldnames=CSV_COLUMNS).writeheader()
        return CSV_COLUMNS

    with chemin.open("r", newline="", encoding="utf-8") as fichier:
        lecteur = csv.DictReader(fichier)
        colonnes_existantes = lecteur.fieldnames or []
        lignes = list(lecteur)

    colonnes = colonnes_existantes + [
        colonne for colonne in CSV_COLUMNS if colonne not in colonnes_existantes
    ]
    if colonnes != colonnes_existantes:
        with chemin.open("w", newline="", encoding="utf-8") as fichier:
            redacteur = csv.DictWriter(fichier, fieldnames=colonnes)
            redacteur.writeheader()
            redacteur.writerows(lignes)
    return colonnes


def creer_session(chemin_csv=CSV_PATH):
    colonnes = _initialiser_csv(chemin_csv)
    session = {colonne: "" for colonne in colonnes}
    session["session_id"] = str(uuid.uuid4())
    session["horodatage"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with Path(chemin_csv).open("a", newline="", encoding="utf-8") as fichier:
        csv.DictWriter(fichier, fieldnames=colonnes).writerow(session)
    return {"session_id": session["session_id"], "horodatage": session["horodatage"]}


def enregistrer_reponse(session_id, question_id, valeur, chemin_csv=CSV_PATH):
    question = next(
        (item for item in QUESTIONS if item["id"] == question_id), None
    )
    if question is None:
        raise ValueError(f"Question inconnue : {question_id}")

    colonnes = _initialiser_csv(chemin_csv)
    chemin = Path(chemin_csv)
    with chemin.open("r", newline="", encoding="utf-8") as fichier:
        lecteur = csv.DictReader(fichier)
        lignes = list(lecteur)

    for ligne in lignes:
        if ligne.get("session_id") == session_id:
            ligne[question["colonne_csv"]] = valeur
            break
    else:
        raise KeyError(f"Session introuvable : {session_id}")

    with chemin.open("w", newline="", encoding="utf-8") as fichier:
        redacteur = csv.DictWriter(fichier, fieldnames=colonnes)
        redacteur.writeheader()
        redacteur.writerows(lignes)


def lire_session(session_id, chemin_csv=CSV_PATH):
    _initialiser_csv(chemin_csv)
    with Path(chemin_csv).open("r", newline="", encoding="utf-8") as fichier:
        for session in csv.DictReader(fichier):
            if session.get("session_id") == session_id:
                return session
    raise KeyError(f"Session introuvable : {session_id}")