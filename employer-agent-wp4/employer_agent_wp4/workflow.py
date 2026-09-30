from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mahara_data.enums import TaxonomyStatus
from mahara_data.schemas.offer import NormalizedJobOffer
from sqlalchemy.orm import Session

from shared_llm import OpenAICompatibleClient

from .prompts import ANSWER_EXTRACTION_SYSTEM_PROMPT, OFFER_GENERATION_SYSTEM_PROMPT


INTERVIEW_FIELDS = (
    "title",
    "responsibilities",
    "location",
    "contract_type",
    "required_skills",
    "preferred_skills",
    "experience_and_education",
    "languages_required",
    "work_mode",
    "positions_count",
    "salary",
)

FIELD_QUESTIONS = {
    "title": "Chnowa esm el poste? / Quel est l'intitulé du poste ?",
    "responsibilities": "Chnowa bech yaamel fel khedma? / Quelles seront ses missions principales ?",
    "location": "Win blassa el khedma (gouvernorat w delegation)? / Où se trouve le poste (gouvernorat et délégation) ?",
    "contract_type": "Chnowa naw3 el contrat? / Quel type de contrat proposez-vous ?",
    "required_skills": "Chnowa el compétences elli lazmin? / Quelles compétences sont indispensables ?",
    "preferred_skills": "Famma compétences zeydin yfadhilhom? / Y a-t-il des compétences souhaitées mais non obligatoires ?",
    "experience_and_education": "Chnowa el expérience w niveau d'études? / Quelle expérience et quel niveau d'études demandez-vous ?",
    "languages_required": "Chnowa el langues w niveauhom? / Quelles langues et quels niveaux sont nécessaires ?",
    "work_mode": "El khedma sur place, à distance wala hybride? / Le travail est-il sur site, à distance ou hybride ?",
    "positions_count": "9addech men personne bech ta3mlou recruter? / Combien de personnes souhaitez-vous recruter ?",
    "salary": "T7eb t7added salaire? (tnajem tskip) / Souhaitez-vous préciser le salaire ? (vous pouvez passer)",
}

REQUIRED_FIELDS = ("title", "responsibilities", "location", "contract_type", "required_skills")


class InterviewError(ValueError):
    pass


def first_question() -> str:
    return FIELD_QUESTIONS[INTERVIEW_FIELDS[0]]


def current_field(state: dict[str, Any]) -> str | None:
    revision_fields = state.get("revision_fields", [])
    if revision_fields:
        return revision_fields[0]
    index = state.get("field_index", 0)
    return INTERVIEW_FIELDS[index] if index < len(INTERVIEW_FIELDS) else None


async def extract_answer(
    client: OpenAICompatibleClient,
    field: str,
    answer: str,
    prior_answers: dict[str, str] | None = None,
) -> tuple[str | None, bool, str | None]:
    result = await client.complete_chat(
        [
            {
                "role": "system",
                "content": ANSWER_EXTRACTION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"field": field, "answer": answer, "prior_answers": prior_answers or {}},
                    ensure_ascii=False,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError as error:
        raise InterviewError("The assistant returned invalid answer data") from error
    if not isinstance(parsed, dict) or not isinstance(parsed.get("skipped"), bool):
        raise InterviewError("The assistant returned incomplete answer data")
    value = parsed.get("value")
    if value is not None and not isinstance(value, str):
        raise InterviewError("The assistant returned an invalid field value")
    clarification = parsed.get("clarification")
    if clarification is not None and not isinstance(clarification, str):
        clarification = None
    return value.strip() if value else None, parsed["skipped"], clarification


async def generate_offer(
    client: OpenAICompatibleClient,
    db: Session,
    state: dict[str, Any],
    employer_id: str,
    skills_model: Any,
    offer_model: type[NormalizedJobOffer] = NormalizedJobOffer,
) -> tuple[dict[str, Any] | None, list[str]]:
    answers = state.get("answers", {})
    missing = [field for field in REQUIRED_FIELDS if not answers.get(field)]
    if missing:
        return None, missing

    query = db.query(skills_model)
    validated_skills = query.filter(skills_model.status == TaxonomyStatus.VALIDATED).all()
    if not validated_skills:
        return None, ["validated_skill_taxonomy"]
    allowed_skills = [
        {"code": skill.code, "label_fr": skill.label_fr, "label_derja": skill.label_derja}
        for skill in validated_skills
    ]
    prompt = {
        "answers": answers,
        "skipped_fields": state.get("skipped", []),
        "employer_id": employer_id,
        "allowed_skills": allowed_skills,
        "offer_schema": offer_model.model_json_schema(),
    }
    result = await client.complete_chat(
        [
            {
                "role": "system",
                "content": OFFER_GENERATION_SYSTEM_PROMPT,
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, default=str)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    try:
        payload = json.loads(result)
        payload["employer_id"] = employer_id
        validated = offer_model.model_validate(payload)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return None, [f"offer_validation: {error}"]
    allowed_codes = {skill["code"] for skill in allowed_skills}
    invalid_codes = [skill.skill_code for skill in validated.skills if skill.skill_code not in allowed_codes]
    if invalid_codes:
        return None, ["unrecognized_skill_codes"]
    return validated.model_dump(mode="json"), []


def next_question(state: dict[str, Any]) -> str | None:
    field = current_field(state)
    return FIELD_QUESTIONS[field] if field else None