from pathlib import Path


AUDIO_DIR = Path(__file__).resolve().parent / "audio_questions"

QUESTIONS = [
    {
        "id": "metier",
        "texte": "Quel métier exercez-vous ?",
        "chemin_audio": AUDIO_DIR / "job question .aac",
        "colonne_csv": "metier",
        "type_reponse": "métier",
    },
    {
        "id": "date",
        "texte": "À partir de quelle date êtes-vous disponible ?",
        "chemin_audio": AUDIO_DIR / "date question .aac",
        "colonne_csv": "date_disponibilite",
        "type_reponse": "date",
    },
    {
        "id": "gouvernorat",
        "texte": "Dans quel gouvernorat habitez-vous ?",
        "chemin_audio": AUDIO_DIR / "wileya question .aac",
        "colonne_csv": "gouvernorat",
        "type_reponse": "gouvernorat",
    },
    {
        "id": "telephone",
        "texte": "Quel est votre numéro de téléphone ?",
        "chemin_audio": AUDIO_DIR / "num phone question .aac",
        "colonne_csv": "telephone",
        "type_reponse": "téléphone",
    },
    {
        "id": "texte_libre",
        "texte": "Avez-vous une autre information à ajouter ?",
        "chemin_audio": None,
        "colonne_csv": "texte_libre",
        "type_reponse": "texte libre",
    },
]