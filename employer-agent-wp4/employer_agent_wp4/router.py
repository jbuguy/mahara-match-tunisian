from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from mahara_data.db.models.taxonomy import Skill
from mahara_data.schemas.offer import NormalizedJobOffer
from shared_llm import LLMError, OpenAICompatibleClient

from .workflow import (
    FIELD_QUESTIONS,
    INTERVIEW_FIELDS,
    REQUIRED_FIELDS,
    InterviewError,
    build_offer_review,
    current_field,
    extract_answer,
    first_question,
    generate_offer,
    next_question,
)


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class DraftUpdate(BaseModel):
    draft: dict[str, Any]


class SessionCreate(BaseModel):
    mode: Literal["chat", "form"] = "chat"


class FormSubmission(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


def create_employer_agent_router(
    get_db: Callable[..., Any],
    get_current_employer: Callable[..., Any],
    session_model: type,
    *,
    llm_client: OpenAICompatibleClient | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/employer-agent", tags=["employer-agent"])
    client = llm_client or OpenAICompatibleClient()
    static_dir = Path(__file__).parent / "static"

    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    def chat_ui() -> Any:
        built_app = static_dir / "index.html"
        if built_app.is_file():
            return FileResponse(built_app)
        raise HTTPException(status_code=503, detail="The employer interface has not been built")

    @router.get("/assets/{asset_path:path}", include_in_schema=False)
    def ui_asset(asset_path: str) -> FileResponse:
        assets_dir = (static_dir / "assets").resolve()
        asset = (assets_dir / asset_path).resolve()
        if not asset.is_relative_to(assets_dir) or not asset.is_file():
            raise HTTPException(status_code=404, detail="Asset not found")
        return FileResponse(asset)

    @router.post("/sessions", status_code=status.HTTP_201_CREATED)
    def create_session(
        payload: SessionCreate | None = None,
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        mode = payload.mode if payload else "chat"
        session = session_model(
            employer_id=current.id,
            state={"field_index": 0, "answers": {}, "skipped": [], "mode": mode},
            messages=[{"role": "assistant", "content": first_question()}] if mode == "chat" else [],
            draft=None,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return _session_response(session)

    @router.post("/sessions/{session_id}/answers")
    async def submit_form_answers(
        session_id: uuid.UUID,
        payload: FormSubmission,
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        session = _owned_session(db, session_model, session_id, current.id)
        if session.state.get("mode", "chat") != "form":
            raise HTTPException(status_code=409, detail="This session uses conversational mode")
        if session.draft is not None:
            raise HTTPException(status_code=409, detail="The offer draft has already been generated")
        unknown_fields = set(payload.answers) - set(INTERVIEW_FIELDS)
        if unknown_fields:
            raise HTTPException(status_code=422, detail=f"Unknown interview fields: {', '.join(sorted(unknown_fields))}")
        answers = {field: value.strip() for field, value in payload.answers.items() if value.strip()}
        missing = [field for field in REQUIRED_FIELDS if not answers.get(field)]
        if missing:
            raise HTTPException(status_code=422, detail={"missing_fields": missing})

        state = dict(session.state or {})
        state["answers"] = answers
        state["skipped"] = [field for field in INTERVIEW_FIELDS if field not in answers]
        state["field_index"] = len(INTERVIEW_FIELDS)
        state.pop("revision_fields", None)
        session.messages = [{"role": "assistant", "content": "Merci. Je prépare une première version de l'offre."}]
        try:
            session.draft, missing_fields = await generate_offer(client, db, state, str(current.id), Skill)
        except LLMError as error:
            db.rollback()
            raise HTTPException(status_code=502, detail="Could not generate the job-post draft") from error

        state["missing_fields"] = missing_fields
        if session.draft is None:
            if "validated_skill_taxonomy" in missing_fields:
                session.messages.append(
                    {
                        "role": "assistant",
                        "content": "Les compétences ne sont pas encore disponibles dans le référentiel validé. Le brouillon est conservé; réessayez après l'activation du référentiel.",
                    }
                )
            else:
                session.messages.append(
                    {"role": "assistant", "content": "La première version n'a pas pu être validée. Modifiez les réponses signalées puis réessayez."}
                )
        else:
            session.messages.append({"role": "assistant", "content": "Votre première version est prête à relire."})
        session.state = state
        db.commit()
        db.refresh(session)
        return _session_response(session)

    @router.get("/sessions")
    def list_sessions(
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> list[dict[str, Any]]:
        sessions = (
            db.query(session_model)
            .filter(session_model.employer_id == current.id)
            .order_by(session_model.updated_at.desc())
            .limit(20)
            .all()
        )
        return [_session_response(session) for session in sessions]

    @router.get("/sessions/{session_id}")
    def get_session(
        session_id: uuid.UUID,
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        session = _owned_session(db, session_model, session_id, current.id)
        return _session_response(session)

    @router.get("/sessions/{session_id}/review")
    def get_offer_review(
        session_id: uuid.UUID,
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        session = _owned_session(db, session_model, session_id, current.id)
        if session.draft is None:
            raise HTTPException(status_code=409, detail="This session does not have a generated draft")
        return build_offer_review(db, session.draft)

    @router.patch("/sessions/{session_id}/draft")
    def update_draft(
        session_id: uuid.UUID,
        payload: DraftUpdate,
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        session = _owned_session(db, session_model, session_id, current.id)
        if session.draft is None:
            raise HTTPException(status_code=409, detail="This session does not have a generated draft")
        if session.draft.get("status") == "published":
            raise HTTPException(status_code=409, detail="Published offers cannot be edited")
        candidate = dict(payload.draft)
        original_skill_codes = {skill["skill_code"] for skill in session.draft.get("skills", [])}
        edited_skill_codes = {skill.get("skill_code") for skill in candidate.get("skills", [])}
        if not edited_skill_codes.issubset(original_skill_codes):
            raise HTTPException(
                status_code=422,
                detail="New skills must be resolved against the validated WP1 taxonomy before editing",
            )
        candidate["employer_id"] = str(current.id)
        candidate["status"] = "draft"
        candidate["source"] = "employer_form"
        try:
            validated = NormalizedJobOffer.model_validate(candidate)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        session.draft = validated.model_dump(mode="json")
        db.commit()
        db.refresh(session)
        return _session_response(session)

    @router.post("/sessions/{session_id}/publish")
    def publish_draft(
        session_id: uuid.UUID,
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        session = _owned_session(db, session_model, session_id, current.id)
        if session.draft is None:
            raise HTTPException(status_code=409, detail="This session does not have a generated draft")
        if session.draft.get("status") == "published":
            raise HTTPException(status_code=409, detail="This offer has already been published")

        candidate = dict(session.draft)
        candidate["offer_id"] = candidate.get("offer_id") or str(uuid.uuid4())
        candidate["employer_id"] = str(current.id)
        candidate["status"] = "published"
        candidate["source"] = "employer_form"
        candidate["published_at"] = datetime.now(timezone.utc)
        try:
            validated = NormalizedJobOffer.model_validate(candidate)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        session.draft = validated.model_dump(mode="json")
        session.messages = [
            *session.messages,
            {"role": "assistant", "content": "Votre offre est publiée et visible par les candidats."},
        ]
        db.commit()
        db.refresh(session)
        return _session_response(session)

    @router.post("/sessions/{session_id}/messages")
    async def post_message(
        session_id: uuid.UUID,
        payload: MessageRequest,
        current: Any = Depends(get_current_employer),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        session = _owned_session(db, session_model, session_id, current.id)
        state = dict(session.state or {})
        field = current_field(state)
        if field is None:
            raise HTTPException(status_code=409, detail="The interview is already complete")
        session.messages = [*session.messages, {"role": "user", "content": payload.message}]
        try:
            value, skipped, clarification = await extract_answer(
                client,
                field,
                payload.message,
                prior_answers=state.get("answers", {}),
            )
        except (LLMError, InterviewError) as error:
            db.rollback()
            raise HTTPException(status_code=502, detail="Could not process that answer; please try again") from error

        if clarification:
            session.messages = [*session.messages, {"role": "assistant", "content": clarification}]
            db.commit()
            return _session_response(session)
        if skipped:
            state["skipped"] = [*state.get("skipped", []), field]
        elif value is None:
            reply = clarification or "Ma fhemtch el jawab. Tnajem twadhe7li? / Je n'ai pas bien compris. Pouvez-vous préciser ?"
            session.messages = [*session.messages, {"role": "assistant", "content": reply}]
            db.commit()
            return _session_response(session)
        else:
            state.setdefault("answers", {})[field] = value

        if state.get("revision_fields"):
            state["revision_fields"] = state["revision_fields"][1:]
        else:
            state["field_index"] += 1
        session.state = state
        question = next_question(state)
        if question:
            session.messages = [*session.messages, {"role": "assistant", "content": question}]
        else:
            session.messages = [
                *session.messages,
                {"role": "assistant", "content": "Merci. Je prépare une première version de l'offre. / Yaaychek, taw n7adher version loula mel offre."},
            ]
            try:
                session.draft, missing = await generate_offer(client, db, state, str(current.id), Skill)
            except LLMError as error:
                db.rollback()
                raise HTTPException(status_code=502, detail="Could not generate the job-post draft") from error
            state["missing_fields"] = missing
            recoverable = [field for field in missing if field in FIELD_QUESTIONS]
            if recoverable:
                state["revision_fields"] = recoverable
                question = next_question(state)
                session.messages = [
                    *session.messages,
                    {
                        "role": "assistant",
                        "content": "Pour éviter d'inventer des informations, précisez ces éléments obligatoires. / Bech ma nkhammench ma3loumet, lawwej 3al ma3loumet el lezma:",
                    },
                    {"role": "assistant", "content": question},
                ]
            elif "validated_skill_taxonomy" in missing:
                session.messages = [
                    *session.messages,
                    {
                        "role": "assistant",
                        "content": "Les compétences ne sont pas encore disponibles dans le référentiel validé. Le brouillon est conservé; réessayez après l'activation du référentiel. / El compétences mazelt mch mawjoudin fel référentiel validé. Le brouillon reste enregistré.",
                    },
                ]
            session.state = state
        db.commit()
        db.refresh(session)
        return _session_response(session)

    return router


def _owned_session(db: Session, session_model: type, session_id: uuid.UUID, employer_id: uuid.UUID) -> Any:
    session = db.get(session_model, session_id)
    if session is None or session.employer_id != employer_id:
        raise HTTPException(status_code=404, detail="Draft session not found")
    return session


def _session_response(session: Any) -> dict[str, Any]:
    return {
        "id": str(session.id),
        "mode": session.state.get("mode", "chat"),
        "messages": session.messages,
        "answers": session.state.get("answers", {}),
        "skipped": session.state.get("skipped", []),
        "current_field": current_field(session.state),
        "complete": session.draft is not None or current_field(session.state) is None,
        "missing_fields": session.state.get("missing_fields", []),
        "draft": session.draft,
    }