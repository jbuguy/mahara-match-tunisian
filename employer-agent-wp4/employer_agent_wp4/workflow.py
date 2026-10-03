from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from mahara_data.db.models.market import MarketDataset, MarketIndicator
from mahara_data.db.models.taxonomy import Occupation, Skill
from mahara_data.enums import MarketIndicatorType, TaxonomyStatus
from mahara_data.schemas.offer import NormalizedJobOffer
from sqlalchemy.exc import SQLAlchemyError
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
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "answer_extraction",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "value": {"type": ["string", "null"]},
                        "skipped": {"type": "boolean"},
                        "clarification": {"type": ["string", "null"]},
                    },
                    "required": ["value", "skipped", "clarification"],
                    "additionalProperties": False,
                },
            },
        },
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
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "normalized_job_offer",
                "strict": True,
                "schema": offer_model.model_json_schema(),
            },
        },
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


def build_offer_review(
    db: Session,
    draft: dict[str, Any],
    *,
    today: date | None = None,
    max_market_age_days: int = 548,
) -> dict[str, Any]:
    today = today or date.today()
    salary = draft.get("salary")
    salary_review: dict[str, Any] = {
        "status": "not_provided" if not salary else "unavailable",
        "message": (
            "No salary range is listed. Consider adding one so applicants can assess the role."
            if not salary
            else "A relevant, current salary benchmark is not available for this role and location."
        ),
        "benchmark": None,
    }

    if salary and draft.get("occupation_code") and draft.get("location", {}).get("governorate_code"):
        try:
            occupation = db.query(Occupation).filter(Occupation.code == draft["occupation_code"]).first()
            if occupation is not None:
                indicator = (
                    db.query(MarketIndicator)
                    .filter(
                        MarketIndicator.indicator_type == MarketIndicatorType.MEDIAN_SALARY,
                        MarketIndicator.occupation_id == occupation.id,
                        MarketIndicator.governorate_code == draft["location"]["governorate_code"],
                        MarketIndicator.unit == "tnd",
                    )
                    .order_by(MarketIndicator.period_end.desc())
                    .first()
                )
                if indicator is not None:
                    dataset = db.query(MarketDataset).filter(MarketDataset.id == indicator.dataset_id).first()
                    if dataset is not None:
                        market_period = (indicator.extra or {}).get("period") or (indicator.extra or {}).get("salary_period")
                        salary_period = salary.get("period", "month")
                        period_end = indicator.period_end
                        benchmark = {
                            "median_tnd": float(indicator.value),
                            "period": market_period,
                            "publisher": dataset.publisher,
                            "dataset": dataset.title,
                            "period_start": indicator.period_start.isoformat(),
                            "period_end": period_end.isoformat(),
                        }
                        salary_review["benchmark"] = benchmark
                        if period_end < today - timedelta(days=max_market_age_days):
                            salary_review.update(
                                status="stale",
                                message="A matching salary record exists, but it is too old to use as a current comparison.",
                            )
                        elif market_period != salary_period:
                            salary_review.update(
                                status="period_mismatch" if market_period else "period_unknown",
                                message="A salary record exists, but its pay period does not match this offer's salary period.",
                            )
                        else:
                            minimum = salary.get("min_tnd")
                            maximum = salary.get("max_tnd")
                            if minimum is None or maximum is None:
                                comparison = "incomplete_range"
                                message = "The offer has an incomplete salary range, so it cannot be compared with the median."
                            elif maximum < indicator.value:
                                comparison = "below_median"
                                message = "The offered range is below this market median; consider whether it reflects the role and budget."
                            elif minimum > indicator.value:
                                comparison = "above_median"
                                message = "The offered range is above this market median."
                            else:
                                comparison = "includes_median"
                                message = "The offered range includes this market median."
                            salary_review.update(status="matched", comparison=comparison, message=message)
        except SQLAlchemyError:
            db.rollback()
            salary_review.update(
                status="unavailable",
                message="Market salary data is not currently available for comparison.",
                benchmark=None,
            )

    skills = draft.get("skills", [])
    required_skills = [skill for skill in skills if skill.get("requirement") == "required"]
    suggestions = []
    if len(required_skills) >= 5:
        suggestions.append(
            {
                "field": "skills",
                "message": f"{len(required_skills)} skills are marked required. Consider whether any are preferences rather than essentials.",
            }
        )
    if draft.get("min_years_experience", 0) >= 5:
        suggestions.append(
            {
                "field": "min_years_experience",
                "message": "Review whether this experience threshold is essential for the listed responsibilities; lowering it may widen the eligible pool.",
            }
        )
    if draft.get("education_level_min") and draft.get("min_years_experience", 0) >= 5:
        suggestions.append(
            {
                "field": "education_level_min",
                "message": "You require both a minimum education level and substantial experience. Check that both are necessary for the role.",
            }
        )
    if len(draft.get("languages_required", [])) >= 3:
        suggestions.append(
            {
                "field": "languages_required",
                "message": "Three or more languages are listed. Consider marking any nonessential languages as preferred in the offer description.",
            }
        )

    skill_codes = {skill.get("skill_code") for skill in skills}
    skill_labels = {}
    if skill_codes:
        try:
            for skill in db.query(Skill).filter(Skill.code.in_(skill_codes)).all():
                skill_labels[skill.code] = skill.label_fr
        except SQLAlchemyError:
            db.rollback()
    candidate_snapshot = {
        "title": draft.get("title"),
        "responsibilities": draft.get("description"),
        "experience_years_min": draft.get("min_years_experience", 0),
        "education_level_min": draft.get("education_level_min"),
        "location": draft.get("location"),
        "work_mode": draft.get("work_mode"),
        "skills": [
            {
                "label": skill_labels.get(skill.get("skill_code"), skill.get("skill_code")),
                "requirement": skill.get("requirement"),
                "min_level": skill.get("min_level", 1),
            }
            for skill in skills
        ],
        "languages_required": draft.get("languages_required", []),
    }
    return {
        "salary": salary_review,
        "requirement_suggestions": suggestions,
        "candidate_snapshot": candidate_snapshot,
    }