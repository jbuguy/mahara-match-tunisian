import mimetypes
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from mahara_data.db.models.candidates import ConversationSession
from mahara_data.enums import ConversationChannel, OnboardingPath, ProcessingStatus
from mahara_voice import read_limited
from sqlalchemy.orm import Session

from ...models import Candidate, CandidateOnboardingSession
from .offre_generator import generer_offre_ecrite

FEATURE_ROOT = Path(__file__).resolve().parent
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

from .questions import QUESTIONS
from .stt_adapter import transcrire_et_extraire

def _current_question(answers: dict[str, Any]):
    for question in QUESTIONS:
        answer_key = question["colonne_csv"]
        if not str(answers.get(answer_key, "")).strip():
            return question
    return None

def _question_payload(question):
    return {
        "id": question["id"],
        "texte": question["texte"],
        "audio_url": f"/api/v1/onboarding/questions/{question['id']}/audio",
    }

def _session_or_404(db: Session, session_id: uuid.UUID, user_id: uuid.UUID):
    session = (
        db.query(CandidateOnboardingSession)
        .filter(
            CandidateOnboardingSession.id == session_id,
            CandidateOnboardingSession.user_id == user_id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return session

def create_onboarding_router(get_db: Any, get_current_user: Any) -> APIRouter:
    router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

    @router.post("/sessions", status_code=201)
    def create_session(
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        session = CandidateOnboardingSession(user_id=user.id, answers={}, status="active")
        db.add(session)
        db.commit()
        db.refresh(session)
        return {
            "session_id": str(session.id),
            "question": _question_payload(QUESTIONS[0]),
        }

    @router.get("/sessions/{session_id}")
    def get_session(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        session = _session_or_404(db, session_id, user.id)
        question = _current_question(session.answers)
        return {
            "session_id": str(session.id),
            "termine": question is None,
            "question": _question_payload(question) if question else None,
            "answers": session.answers if question is None else {},
        }

    @router.get("/sessions/{session_id}/offre", response_class=PlainTextResponse)
    def get_generated_offer(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ) -> str:
        session = _session_or_404(db, session_id, user.id)
        if _current_question(session.answers) is not None:
            raise HTTPException(status_code=409, detail="La session doit être terminée")
        return generer_offre_ecrite(session.answers)

    @router.post("/sessions/{session_id}/finalize")
    def finalize_session(
        session_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        session = _session_or_404(db, session_id, user.id)
        if _current_question(session.answers) is not None:
            raise HTTPException(status_code=409, detail="Cette session d'accueil n'est pas terminÃ©e")

        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None or candidate.consent_given_at is None:
            raise HTTPException(status_code=409, detail="Enregistrez votre profil avec votre consentement avant de terminer l'accueil")

        conversation = db.get(ConversationSession, session.id)
        if conversation is not None and conversation.candidate_id not in (None, candidate.id):
            raise HTTPException(status_code=409, detail="Cette session est dÃ©jÃ  associÃ©e Ã  un autre profil")

        onboarding_path = (
            OnboardingPath.DERJA_GUIDED_VOICE
            if candidate.literacy_level == "non_literate"
            else OnboardingPath.DERJA_DETAILED
        )
        if conversation is None:
            conversation = ConversationSession(
                id=session.id,
                candidate_id=candidate.id,
                channel=ConversationChannel.AUDIO,
                onboarding_path=onboarding_path,
                language="ar-TN",
                status=ProcessingStatus.COMPLETED,
                transcript=[],
                detected_intents=[],
                appetence={},
                ended_at=datetime.now(UTC),
            )
            db.add(conversation)
        elif conversation.candidate_id is None:
            conversation.candidate_id = candidate.id

        candidate.onboarding_path = conversation.onboarding_path.value
        db.commit()
        return {
            "session_id": str(session.id),
            "candidate_id": str(candidate.id),
            "onboarding_path": candidate.onboarding_path,
            "status": "linked",
        }

    @router.post("/sessions/{session_id}/reponse")
    def submit_answer(
        session_id: uuid.UUID,
        audio: Annotated[UploadFile, File()],
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[Any, Depends(get_current_user)],
    ):
        session = _session_or_404(db, session_id, user.id)
        question = _current_question(session.answers)
        if question is None:
            raise HTTPException(status_code=409, detail="Cette session est dÃ©jÃ  terminÃ©e")

        content = read_limited(audio.file, MAX_AUDIO_BYTES)
        if not content:
            raise HTTPException(
                status_code=400,
                detail={"code": "audio_vide", "message": "Enregistrez une rÃ©ponse puis rÃ©essayez."},
            )
        if len(content) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Fichier audio trop volumineux (25 Mo maximum)")

        suffix = MIME_SUFFIXES.get(audio.content_type or "") or Path(audio.filename or "").suffix.lower()
        if suffix not in {".aac", ".m4a", ".mp3", ".ogg", ".wav", ".webm"}:
            raise HTTPException(status_code=415, detail="Format audio non pris en charge")

        try:
            with tempfile.TemporaryDirectory(prefix="mahara-onboarding-") as temp_dir:
                source_path = Path(temp_dir) / f"answer{suffix}"
                source_path.write_bytes(content)
                audio_path = source_path
                if suffix != ".wav":
                    try:
                        from pydub import AudioSegment
                    except ImportError as error:
                        raise HTTPException(
                            status_code=503,
                            detail="Le traitement audio onboarding n'est pas installÃ©",
                        ) from error
                    segment = AudioSegment.from_file(source_path)
                    if len(segment) == 0:
                        raise HTTPException(
                            status_code=400,
                            detail={"code": "audio_vide", "message": "L'audio ne contient aucun son. RÃ©essayez."},
                        )
                    audio_path = source_path.with_suffix(".wav")
                    segment.export(audio_path, format="wav")
                try:
                    result = transcrire_et_extraire(str(audio_path), question["type_reponse"])
                except ImportError as error:
                    raise HTTPException(status_code=503, detail="Le moteur STT onboarding n'est pas installÃ©") from error
                except Exception as error:
                    raise HTTPException(
                        status_code=500,
                        detail={"code": "transcription_echec", "message": "La transcription a Ã©chouÃ©."},
                    ) from error
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(
                status_code=400,
                detail={"code": "audio_invalide", "message": "Format audio illisible; envoyez un fichier valide."},
            ) from error

        raw_text = str(result.get("texte_brut") or "").strip()
        if not raw_text:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "transcription_vide",
                    "message": "Aucune rÃ©ponse reconnue. Vous pouvez rÃ©enregistrer et rÃ©essayer.",
                    "reessayer": True,
                },
            )

        value = result.get("valeur_extraite") or raw_text
        answers = dict(session.answers)
        answers[question["colonne_csv"]] = value
        session.answers = answers
        next_question = _current_question(answers)
        if next_question is None:
            session.status = "completed"
        db.commit()

        return {
            "texte_brut": raw_text,
            "valeur_extraite": result.get("valeur_extraite"),
            "question_suivante": _question_payload(next_question) if next_question else None,
            "termine": next_question is None,
        }

    @router.get("/questions/{question_id}/audio")
    def get_question_audio(question_id: str):
        question = next((item for item in QUESTIONS if item["id"] == question_id), None)
        if question is None or question["chemin_audio"] is None:
            raise HTTPException(status_code=404, detail="Audio de question introuvable")

        audio_path = Path(question["chemin_audio"])
        if not audio_path.is_absolute():
            audio_path = FEATURE_ROOT / audio_path
        if not audio_path.is_file():
            raise HTTPException(status_code=404, detail="Audio de question introuvable")
        return FileResponse(
            audio_path,
            media_type=mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream",
            filename=audio_path.name,
        )

    return router

