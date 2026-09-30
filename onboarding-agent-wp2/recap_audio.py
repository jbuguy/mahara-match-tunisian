from pathlib import Path

from pydub import AudioSegment

import csv_store
from questions import QUESTIONS


PROJECT_DIR = Path(__file__).resolve().parent
REPONSES_DIR = PROJECT_DIR / "data" / "audio_reponses"
RECAPS_DIR = PROJECT_DIR / "data" / "recaps"
SILENCE_MS = 500
FRAME_RATE = 44100


def _charger_segment(chemin):
    with Path(chemin).open("rb") as fichier_audio:
        return (
            AudioSegment.from_file(fichier_audio)
            .set_frame_rate(FRAME_RATE)
            .set_channels(1)
            .set_sample_width(2)
        )


def generer_recap_audio(session_id):
    session = csv_store.lire_session(session_id, csv_store.CSV_PATH)
    chemin_recap = RECAPS_DIR / f"{session_id}.wav"
    if chemin_recap.is_file():
        return chemin_recap

    segments = []
    for question in QUESTIONS:
        valeur = session.get(question["colonne_csv"])
        if not str(valeur or "").strip():
            raise ValueError("La session n'est pas terminée")

        chemin_question = Path(question["chemin_audio"])
        if not chemin_question.is_absolute():
            chemin_question = PROJECT_DIR / chemin_question
        chemin_reponse = REPONSES_DIR / session_id / f"{question['id']}.wav"
        for chemin in (chemin_question, chemin_reponse):
            if not chemin.is_file():
                raise FileNotFoundError(f"Audio introuvable : {chemin}")
            segments.append(_charger_segment(chemin))

    silence = AudioSegment.silent(duration=SILENCE_MS, frame_rate=FRAME_RATE)
    silence = silence.set_channels(1).set_sample_width(2)
    recap = segments[0]
    for segment in segments[1:]:
        recap += silence + segment

    RECAPS_DIR.mkdir(parents=True, exist_ok=True)
    with chemin_recap.open("wb") as fichier_recap:
        recap.export(fichier_recap, format="wav")
    return chemin_recap