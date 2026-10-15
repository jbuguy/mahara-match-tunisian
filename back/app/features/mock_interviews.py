"""Private, non-evaluative candidate mock interviews."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from mahara_data.db.models.candidates import Candidate, MockInterviewSession
from mahara_data.db.models.employers import Application, JobOffer, JobOfferSkill
from mahara_data.db.models.taxonomy import Skill
from mahara_data.db.models.taxonomy import Occupation
from mahara_data.enums import TaxonomyStatus
from shared_llm import LLMError, OpenAICompatibleClient


class StartRequest(BaseModel):
    target_title: str = Field(min_length=2, max_length=200)
    occupation_code: str | None = Field(default=None, max_length=32)
    target_offer_id: uuid.UUID | None = None
    language: str = Field(pattern="^(fr|ar|derja)$")
    question_count: Literal[3, 5, 8]
    consent: bool


class AnswerRequest(BaseModel):
    question_index: int = Field(ge=0, le=7)
    answer: str = Field(min_length=1, max_length=8000)


class SaveRequest(BaseModel):
    saved: bool


class DraftAnswerRequest(BaseModel):
    answer: str = Field(default="", max_length=8000)


class Question(BaseModel):
    theme: str = Field(min_length=2, max_length=100)
    prompt: str = Field(min_length=8, max_length=1000)
    follow_up: str = Field(default="", max_length=600)
    tip: str = Field(default="", max_length=500)


class AnswerFeedback(BaseModel):
    question_index: int = Field(ge=0, le=7)
    strength: str = Field(min_length=2, max_length=800)
    improvement: str = Field(min_length=2, max_length=800)
    example: str = Field(min_length=2, max_length=1000)


class TopicFeedback(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    status: str = Field(min_length=2, max_length=60)
    evidence: str = Field(min_length=2, max_length=800)
    next_step: str = Field(min_length=2, max_length=500)


class Review(BaseModel):
    overall_summary: str = Field(min_length=10, max_length=1200)
    topics: list[TopicFeedback] = Field(min_length=2, max_length=5)
    answers: list[AnswerFeedback] = Field(min_length=1, max_length=8)


async def _json_completion(client: OpenAICompatibleClient, messages: list[dict[str, str]]) -> Any:
    try:
        raw = await client.complete_chat(messages, response_format={"type": "json_object"}, temperature=0.3)
        return json.loads(raw)
    except (LLMError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="The coaching service is unavailable. Your answers are saved; try again shortly.") from error


def _session_out(session: MockInterviewSession) -> dict[str, Any]:
    current = len(session.answers)
    return {
        "session_id": str(session.id), "target_title": session.target_title,
        "occupation_code": session.occupation_code,
        "target_offer_id": str(session.target_offer_id) if session.target_offer_id else None,
        "language": session.language,
        "question_count": session.question_count, "questions": session.questions,
        "answers": session.answers, "current_index": current,
        "draft_answer": session.draft_answer,
        "status": session.status, "saved": session.saved, "feedback": session.feedback,
    }


def create_mock_interview_router(get_db: Any, require_candidate: Any, client: OpenAICompatibleClient) -> APIRouter:
    router = APIRouter(prefix="/api/v1/me/mock-interviews", tags=["mock-interviews"])

    def owned_session(db: Session, candidate_id: uuid.UUID, session_id: uuid.UUID) -> MockInterviewSession:
        row = db.query(MockInterviewSession).filter(
            MockInterviewSession.id == session_id,
            MockInterviewSession.candidate_id == candidate_id,
            MockInterviewSession.expires_at > datetime.now(timezone.utc),
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Mock interview not found or expired")
        return row

    @router.get("")
    def list_sessions(user=Depends(require_candidate), db: Session = Depends(get_db)):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            return {"items": []}
        now = datetime.now(timezone.utc)
        db.query(MockInterviewSession).filter(
            MockInterviewSession.candidate_id == candidate.id,
            MockInterviewSession.expires_at <= now,
        ).delete(synchronize_session=False)
        db.commit()
        items = db.query(MockInterviewSession).filter(
            MockInterviewSession.candidate_id == candidate.id,
            MockInterviewSession.saved.is_(True),
        ).order_by(MockInterviewSession.expires_at.desc()).limit(20).all()
        return {"items": [_session_out(row) for row in items]}

    @router.post("", status_code=201)
    async def start_session(payload: StartRequest, user=Depends(require_candidate), db: Session = Depends(get_db)):
        if payload.consent is not True:
            raise HTTPException(status_code=422, detail="Consent to private AI processing is required to start")
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=409, detail="Complete your candidate profile before starting an interview")
        occupation = None
        target_offer = None
        offer_context = ""
        if payload.target_offer_id:
            application = db.query(Application).filter(
                Application.candidate_id == candidate.id,
                Application.job_offer_id == payload.target_offer_id,
            ).first()
            if application is None:
                raise HTTPException(status_code=404, detail="Choose one of your own applications")
            target_offer = db.get(JobOffer, payload.target_offer_id)
            if target_offer is None:
                raise HTTPException(status_code=404, detail="The job offer is no longer available")
            skill_rows = db.query(Skill.code, Skill.label_fr, JobOfferSkill.requirement).join(
                JobOfferSkill, JobOfferSkill.skill_id == Skill.id
            ).filter(JobOfferSkill.job_offer_id == target_offer.id).limit(20).all()
            offer_context = json.dumps({
                "description": (target_offer.description_raw or "")[:5000],
                "skills": [{"code": code, "label": label, "requirement": str(requirement)} for code, label, requirement in skill_rows],
            }, ensure_ascii=False)
        if payload.occupation_code:
            occupation = db.query(Occupation).filter(
                Occupation.code == payload.occupation_code,
                Occupation.status == TaxonomyStatus.VALIDATED,
            ).first()
            if occupation is None:
                raise HTTPException(status_code=422, detail="Choose an available occupation or enter a custom title")
        title = target_offer.title if target_offer else occupation.title_fr if occupation else payload.target_title.strip()
        language_name = {"fr": "French", "ar": "Modern Standard Arabic", "derja": "Tunisian Derja"}[payload.language]
        prompt = (
            "Create a private practice interview. Return JSON {questions:[{theme,prompt,follow_up,tip}]}. "
            f"Create exactly {payload.question_count} distinct, practical interview questions for: {title}. "
            f"Use this job description and skill context when present, without inventing requirements: {offer_context or 'No specific offer context.'}. "
            f"Write all user-facing text in {language_name}. Ask a mix of behavioral and role-specific questions. "
            "Do not ask for sensitive personal data. Do not grade the candidate or imply a hiring decision. "
            "Make follow_up a short optional clarification question, and tip one calm structuring suggestion."
        )
        raw = await _json_completion(client, [{"role": "system", "content": "You write safe, useful interview practice prompts."}, {"role": "user", "content": prompt}])
        try:
            questions = [Question.model_validate(item).model_dump() for item in raw["questions"]]
            if len(questions) != payload.question_count:
                raise ValueError("incorrect question count")
        except (KeyError, TypeError, ValidationError, ValueError) as error:
            raise HTTPException(status_code=503, detail="Could not prepare interview questions. Please try again.") from error
        now = datetime.now(timezone.utc)
        row = MockInterviewSession(
            candidate_id=candidate.id, target_title=title,
            occupation_code=occupation.code if occupation else None,
            target_offer_id=target_offer.id if target_offer else None,
            language=payload.language, question_count=payload.question_count,
            questions=questions, answers=[], status="in_progress", saved=False,
            consented_at=now, expires_at=now + timedelta(hours=24),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _session_out(row)

    @router.get("/{session_id}")
    def get_session(session_id: uuid.UUID, user=Depends(require_candidate), db: Session = Depends(get_db)):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        return _session_out(owned_session(db, candidate.id, session_id))

    @router.post("/{session_id}/answers")
    def save_answer(session_id: uuid.UUID, payload: AnswerRequest, user=Depends(require_candidate), db: Session = Depends(get_db)):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        row = owned_session(db, candidate.id, session_id)
        if row.status != "in_progress":
            raise HTTPException(status_code=409, detail="This interview is already complete")
        if payload.question_index != len(row.answers) or payload.question_index >= len(row.questions):
            raise HTTPException(status_code=409, detail="The interview question has changed; reload the session")
        answers = list(row.answers)
        answers.append({"question_index": payload.question_index, "answer": payload.answer.strip()})
        row.answers = answers
        row.draft_answer = None
        db.commit()
        return {**_session_out(row), "next_question": row.questions[len(answers)] if len(answers) < len(row.questions) else None}

    @router.patch("/{session_id}/draft-answer")
    def save_draft_answer(session_id: uuid.UUID, payload: DraftAnswerRequest, user=Depends(require_candidate), db: Session = Depends(get_db)):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        row = owned_session(db, candidate.id, session_id)
        if row.status != "in_progress" or len(row.answers) >= row.question_count:
            raise HTTPException(status_code=409, detail="There is no active answer to save")
        row.draft_answer = payload.answer.strip() or None
        db.commit()
        return _session_out(row)

    @router.post("/{session_id}/review")
    async def finish_session(session_id: uuid.UUID, user=Depends(require_candidate), db: Session = Depends(get_db)):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        row = owned_session(db, candidate.id, session_id)
        if row.feedback:
            return _session_out(row)
        if len(row.answers) != row.question_count:
            raise HTTPException(status_code=409, detail="Answer each question before requesting your private review")
        prompt = {
            "target": row.target_title,
            "questions": row.questions,
            "answers": row.answers,
            "requirements": "Give practical, kind coaching. Never give a score, grade, pass/fail verdict, ranking or hiring prediction. Do not infer emotion, confidence, personality, accent or identity. Cite answer evidence and give concrete next steps.",
        }
        raw = await _json_completion(client, [
            {"role": "system", "content": "You are a supportive interview coach. Return valid JSON only."},
            {"role": "user", "content": "Return {overall_summary,topics:[{title,status,evidence,next_step}],answers:[{question_index,strength,improvement,example}]}. Use one brief constructive status label per topic, translated into the session's requested language: " + {"fr": "French", "ar": "Modern Standard Arabic", "derja": "Tunisian Derja"}[row.language] + ". Data: " + json.dumps(prompt, ensure_ascii=False)},
        ])
        try:
            feedback = Review.model_validate(raw).model_dump()
            if len(feedback["answers"]) != row.question_count:
                raise ValueError("answer feedback count mismatch")
        except (ValidationError, ValueError) as error:
            raise HTTPException(status_code=503, detail="The coaching review could not be prepared. Your answers are saved; try again shortly.") from error
        row.feedback = feedback
        row.status = "completed"
        if not row.saved:
            row.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        db.commit()
        return _session_out(row)

    @router.patch("/{session_id}/saved")
    def update_saved(session_id: uuid.UUID, payload: SaveRequest, user=Depends(require_candidate), db: Session = Depends(get_db)):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        row = owned_session(db, candidate.id, session_id)
        row.saved = payload.saved
        row.expires_at = datetime.now(timezone.utc) + (timedelta(days=30) if payload.saved else timedelta(hours=24))
        db.commit()
        return _session_out(row)

    @router.delete("/{session_id}", status_code=204)
    def delete_session(session_id: uuid.UUID, user=Depends(require_candidate), db: Session = Depends(get_db)):
        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            return
        row = owned_session(db, candidate.id, session_id)
        db.delete(row)
        db.commit()

    @router.get("/{session_id}/report.pdf")
    def export_report(session_id: uuid.UUID, user=Depends(require_candidate), db: Session = Depends(get_db)):
        from io import BytesIO
        from fastapi.responses import Response
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        row = owned_session(db, candidate.id, session_id)
        if not row.feedback:
            raise HTTPException(status_code=409, detail="Complete the interview before exporting the advice sheet")
        if row.language != "fr":
            raise HTTPException(status_code=406, detail="Use the candidate browser's print-to-PDF flow for Arabic and Tunisian Derja script support")
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        _, height = letter
        y = height - 54
        pdf.setTitle("Private mock interview coaching")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(48, y, "Private interview practice - coaching notes")
        y -= 28
        pdf.setFont("Helvetica", 10)
        for line in [f"Target: {row.target_title}", "Practice only. No score, ranking, or hiring verdict.", "", row.feedback["overall_summary"]]:
            for wrapped in _wrap(line, 95):
                if y < 60:
                    pdf.showPage(); y = height - 54; pdf.setFont("Helvetica", 10)
                pdf.drawString(48, y, wrapped); y -= 15
        for topic in row.feedback["topics"]:
            for line in ["", f"{topic['status']} - {topic['title']}", f"Evidence: {topic['evidence']}", f"Next step: {topic['next_step']}"]:
                for wrapped in _wrap(line, 95):
                    if y < 60:
                        pdf.showPage(); y = height - 54; pdf.setFont("Helvetica", 10)
                    pdf.drawString(48, y, wrapped); y -= 15
        for feedback in row.feedback["answers"]:
            q_index = feedback["question_index"]
            answer_lines = ["", f"Question {q_index + 1}: {row.questions[q_index]['prompt']}", f"What worked: {feedback['strength']}", f"Try next: {feedback['improvement']}", f"Possible wording: {feedback['example']}"]
            for line in answer_lines:
                for wrapped in _wrap(line, 95):
                    if y < 60:
                        pdf.showPage(); y = height - 54; pdf.setFont("Helvetica", 10)
                    pdf.drawString(48, y, wrapped); y -= 15
        pdf.save()
        return Response(buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=mock-interview-advice.pdf"})

    return router


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        if len(line) + len(word) + (1 if line else 0) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line or not lines:
        lines.append(line)
    return lines
