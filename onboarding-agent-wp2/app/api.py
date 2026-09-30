import mimetypes
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydub import AudioSegment

import csv_store
from offre_generator import generer_offre_ecrite
from questions import QUESTIONS
from recap_audio import generer_recap_audio
from stt_adapter import initialiser_moteur_stt, transcrire_et_extraire


PROJECT_DIR = Path(__file__).resolve().parent.parent
SESSIONS_CSV = csv_store.CSV_PATH
REPONSES_DIR = PROJECT_DIR / "data" / "audio_reponses"
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MIME_SUFFIXES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
}


@asynccontextmanager
async def lifespan(_app):
    initialiser_moteur_stt()
    yield


app = FastAPI(title="Onboarding Agent API", version="1.0.0", lifespan=lifespan)


def _payload_question(question):
    return {
        "id": question["id"],
        "texte": question["texte"],
        "audio_url": f"/audio/questions/{question['id']}",
    }


def _question_courante(session):
    for question in QUESTIONS:
        valeur = session.get(question["colonne_csv"], "")
        if valeur is None or not valeur.strip():
            return question
    return None


def _session_ou_404(session_id):
    try:
        return csv_store.lire_session(session_id, SESSIONS_CSV)
    except KeyError as erreur:
        raise HTTPException(status_code=404, detail="Session introuvable") from erreur


def _reponse_question(question):
    if question is None:
        return {"termine": True, "question": None}
    return {"termine": False, "question": _payload_question(question)}


@app.post("/api/v1/sessions")
def creer_session():
    session = csv_store.creer_session(SESSIONS_CSV)
    question = _question_courante(csv_store.lire_session(session["session_id"], SESSIONS_CSV))
    return {
        "session_id": session["session_id"],
        "question": _payload_question(question),
    }


@app.get("/api/v1/sessions/{session_id}/question")
def obtenir_question(session_id: str):
    session = _session_ou_404(session_id)
    return _reponse_question(_question_courante(session))


@app.get("/api/v1/sessions/{session_id}/offre")
def obtenir_offre(session_id: str):
    session = _session_ou_404(session_id)
    if _question_courante(session) is not None:
        raise HTTPException(status_code=409, detail="La session doit être terminée")
    return PlainTextResponse(generer_offre_ecrite(session_id), media_type="text/plain")


@app.get("/api/v1/sessions/{session_id}/recap-audio")
def obtenir_recap_audio(session_id: str):
    session = _session_ou_404(session_id)
    if _question_courante(session) is not None:
        raise HTTPException(status_code=409, detail="La session doit être terminée")
    chemin_recap = generer_recap_audio(session_id)
    return FileResponse(chemin_recap, media_type="audio/wav", filename=chemin_recap.name)


@app.post("/api/v1/sessions/{session_id}/reponse")
def envoyer_reponse(session_id: str, audio: UploadFile = File(...)):
    session = _session_ou_404(session_id)
    question = _question_courante(session)
    if question is None:
        raise HTTPException(status_code=409, detail="Cette session est déjà terminée")

    contenu = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not contenu:
        raise HTTPException(
            status_code=400,
            detail={"code": "audio_vide", "message": "Enregistrez une réponse puis réessayez."},
        )
    if len(contenu) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Fichier audio trop volumineux (25 Mo maximum)")

    suffixe = MIME_SUFFIXES.get(audio.content_type or "")
    if suffixe is None:
        suffixe = Path(audio.filename or "").suffix.lower()
    if suffixe not in {".aac", ".m4a", ".mp3", ".ogg", ".wav", ".webm"}:
        suffixe = ".audio"

    dossier_session = REPONSES_DIR / session_id
    dossier_session.mkdir(parents=True, exist_ok=True)
    chemin_source = dossier_session / f"{question['id']}_{uuid.uuid4().hex}{suffixe}"
    chemin_audio = chemin_source
    chemin_source.write_bytes(contenu)

    if suffixe != ".wav":
        chemin_wav = chemin_source.with_suffix(".wav")
        try:
            segment = AudioSegment.from_file(chemin_source)
            if len(segment) == 0:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "audio_vide", "message": "L'audio ne contient aucun son. Réessayez."},
                )
            segment.export(chemin_wav, format="wav")
            chemin_audio = chemin_wav
        except HTTPException:
            raise
        except Exception as erreur:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "audio_invalide",
                    "message": "Format audio illisible; envoyez un fichier audio valide.",
                },
            ) from erreur

    try:
        resultat = transcrire_et_extraire(str(chemin_audio), question["type_reponse"])
    except Exception as erreur:
        raise HTTPException(
            status_code=500,
            detail={"code": "transcription_echec", "message": "La transcription a échoué."},
        ) from erreur

    texte_brut = (resultat.get("texte_brut") or "").strip()
    if not texte_brut:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "transcription_vide",
                "message": "Aucune réponse reconnue. Vous pouvez réenregistrer et réessayer.",
                "reessayer": True,
            },
        )

    valeur_extraite = resultat.get("valeur_extraite")
    valeur_a_enregistrer = valeur_extraite if valeur_extraite is not None else texte_brut
    try:
        csv_store.enregistrer_reponse(
            session_id,
            question["id"],
            valeur_a_enregistrer,
            SESSIONS_CSV,
        )
    except KeyError as erreur:
        raise HTTPException(status_code=404, detail="Session introuvable") from erreur

    chemin_audio_accepte = dossier_session / f"{question['id']}.wav"
    chemin_audio.replace(chemin_audio_accepte)
    if chemin_source != chemin_audio and chemin_source.exists():
        chemin_source.unlink()

    session_apres_reponse = _session_ou_404(session_id)
    suivante = _question_courante(session_apres_reponse)
    return {
        "texte_brut": texte_brut,
        "valeur_extraite": valeur_extraite,
        "question_suivante": _payload_question(suivante) if suivante else None,
        "termine": suivante is None,
    }


@app.get("/audio/questions/{question_id}")
def servir_audio_question(question_id: str):
    question = next((item for item in QUESTIONS if item["id"] == question_id), None)
    if question is None or question["chemin_audio"] is None:
        raise HTTPException(status_code=404, detail="Audio de question introuvable")

    chemin_audio = Path(question["chemin_audio"])
    if not chemin_audio.is_absolute():
        chemin_audio = PROJECT_DIR / chemin_audio
    if not chemin_audio.is_file():
        raise HTTPException(status_code=404, detail="Audio de question introuvable")

    media_type = mimetypes.guess_type(chemin_audio.name)[0] or "application/octet-stream"
    return FileResponse(chemin_audio, media_type=media_type, filename=chemin_audio.name)