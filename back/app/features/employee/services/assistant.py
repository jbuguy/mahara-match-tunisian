"""Profile assistant ("Assistant Mahara"): a chat that helps the candidate fill the profile form.

Stateless: the frontend sends the recent conversation and the form as it is now; Groq answers with JSON
{reply, updates, done}; the updates are checked, then skill, job and governorate names become codes.
Nothing is saved here: the candidate reviews the form and presses "Enregistrer" themselves.
"""

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache, lru_cache
from typing import Annotated, Any

import groq
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, BeforeValidator, StringConstraints, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models import Occupation
from ..schemas import (
    AssistantChatIn,
    AssistantChatOut,
    AssistantDraft,
    AssistantUpdates,
    ChatMessage,
    CvExperience,
    CvSkill,
    EducationLevel,
    LANGUAGE_LEVELS,
    LanguageOut,
    OccupationOut,
)
from .cv_import import CatalogSkill, find_phone, find_skills, fold, words

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_MESSAGES = 8  # the free plan allows ~8,000 tokens per minute: keep each request small
MAX_REPLY_CHARS = 1000

NO_KEY = "L'assistant n'est pas disponible pour le moment. Vous pouvez remplir le formulaire vous-même."
BUSY = "Un instant, réessayez dans quelques secondes."
SORRY = "Désolé, l'assistant n'a pas pu répondre. Réessayez, ou remplissez le formulaire vous-même."


class AssistantUnavailable(Exception):
    """Groq failed, is rate-limited or answered something unusable. `message` is shown to the candidate."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@lru_cache
def _client(api_key: str) -> groq.Groq:
    # One quick retry (the SDK waits as Groq's retry-after says); after that the candidate gets BUSY or SORRY.
    return groq.Groq(api_key=api_key, timeout=30, max_retries=1)


def get_groq_client(settings: Settings = Depends(get_settings)) -> groq.Groq:
    """FastAPI dependency: the Groq client, or 503 when GROQ_API_KEY isn't set."""
    if not settings.groq_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=NO_KEY)
    return _client(settings.groq_api_key)


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Assistant Mahara, a friendly Tunisian job-profile assistant. You help a job seeker fill their profile form.
Ask ONE short question at a time about the next missing field, in this order: full name, phone, governorate, education level, skills (and how good they are), past jobs (title, employer, how long), jobs they want, languages, a one-sentence "à propos".
The candidate may write French, Tunisian Derja in Latin letters with numbers (3=ع, 7=ح, 9=ق, 5=خ), Derja in Arabic letters, or Modern Standard Arabic. Your reply MUST use the language and script of the candidate's last message, for example:
"esmi Amine" → "Ahla Amine ! Chnowa noumrou telifounek ?"
"إسمي أمين" → "أهلا أمين ! شنوّة نومرو تليفونك ؟"
"Je m'appelle Amine" → "Merci Amine ! Quel est votre numéro de téléphone ?"
Never invent information and never show codes to the candidate. If an answer is unclear, ask again simply. If the candidate has nothing for a field or doesn't want to answer, go to the next one.
If your last message said a skill or job isn't in our lists, don't move on until the candidate gives another word or says to skip it ("Ignorer").
When everything is filled or the candidate says they are done, set done to true and tell them to check the form and press "Enregistrer".

Answer with a JSON object only: {"reply": "...", "updates": {...}, "asking": "phone", "done": false}
"asking" is the field your reply asks about (one of the keys below), or null.
"updates" holds everything the candidate's last message gives or corrects, even fields you didn't ask about ("men Sousse" gives the governorate). Allowed keys:
- full_name, phone, governorate (its French name)
- education_level: none, primary, lower_secondary, baccalaureate, vocational_cap, vocational_btp, vocational_bts, licence, master, engineer or doctorate
- skills: [{"name": "...", "level": 1-4}] (1 chwaya/un peu, 2 normal/moyen, 3 behi/bien, 4 barcha/expert): every skill named, even without a level (then leave "level" out)
- experiences: [{"job_title": "...", "employer": "...", "months": 24}]
- desired_jobs: ["..."]
- languages: [{"code": "ar", "level": "basic|intermediate|fluent|native"}]
- summary: one sentence
Write skill names, job titles and the summary in French."""

# The fields in the order the assistant asks about them, with the names used in the prompt.
FIELDS = [
    ("full_name", "full name"),
    ("phone", "phone"),
    ("governorate", "governorate"),
    ("education_level", "education level"),
    ("skills", "skills"),
    ("experiences", "past jobs"),
    ("desired_jobs", "jobs they want"),
    ("languages", "languages"),
    ("summary", "à propos"),
]
# "asking" in the model's words → the form field the frontend shows (so the form follows the question).
ASKING = {
    "full_name": "full_name", "phone": "phone", "governorate": "governorate_code", "education_level": "education_level",
    "skills": "skills", "experiences": "experiences", "desired_jobs": "desired_occupations", "languages": "languages",
    "summary": "summary",
}


def _short(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def form_state(draft: AssistantDraft) -> str:
    """The form as the model sees it: what's filled (kept short) and what's still empty.

    The phone number itself isn't sent, only whether it's filled.
    """
    governorate = GOVERNORATE_NAMES.get(draft.governorate_code, "")
    filled: dict[str, Any] = {
        "full_name": _short(draft.full_name),
        "phone": "filled" if draft.phone.strip() else "",
        "governorate": governorate,
        "education_level": draft.education_level.strip(),
        "skills": [f"{_short(s.label_fr, 60)} {s.level or 2}/4" for s in draft.skills[:15]],
        "experiences": [
            _short(", ".join(filter(None, [
                e.job_title_raw.strip(),
                e.employer_name.strip(),
                f"{e.duration_months.strip()} months" if e.duration_months.strip() else "",
            ])), 100)
            for e in draft.experiences[:10]
        ],
        "desired_jobs": [_short(o.title_fr, 60) for o in draft.desired_occupations],
        "languages": [f"{lang.code} {lang.level}" for lang in draft.languages[:10] if lang.code],
        "summary": _short(draft.summary, 200),
    }
    filled = {key: value for key, value in filled.items() if value}
    empty = [label for key, label in FIELDS if key not in filled]
    state = "The form now: " + json.dumps(filled, ensure_ascii=False)
    return state + ("\nStill empty: " + ", ".join(empty) + "." if empty else "\nEvery field is filled.")


# Words that tell Derja written in Latin letters from French (on folded text).
DERJA_WORDS = set(
    "esmi ismi ena ana men mel chnowa chnoua chniya nheb n7eb nekhdem khdemt khdamt na3ref n3ref narf barcha "
    "barsha chwaya chwaia behi bahi mouch mech mich 3and w ya ey eyh aya yezzi sahit 3aslema ahla mte3 mta3 "
    "kifech kima tawa taw zeda lezem nahki n9ra 9rit snin chhar 3am wala ama belehi saha labes nesker noskon "
    "sakna saken fil fel".split()
)
FRENCH_WORDS = set(
    "je j suis le la les de des du et mon ma mes est c ai un une en pour avec bonjour merci oui non dans m "
    "appelle habite travaille parle sais peu bien tres mais aussi".split()
)
DIGIT_IN_WORD = re.compile(r"^[a-z]*[35679][a-z]+$|^[a-z]+[35679][a-z]*$")  # na3ref, 9bal, mli7
ARABIC_LETTER = re.compile(r"[ء-ي]")


def candidate_language(messages: list[ChatMessage]) -> str | None:
    """'arabic', 'derja' (in Latin letters) or 'french', from the candidate's last message that has words in it."""
    for message in reversed(messages):
        if message.role != "user":
            continue
        text = message.content
        latin = len(re.findall(r"[a-zA-Z]", text))
        if ARABIC_LETTER.search(text) and len(ARABIC_LETTER.findall(text)) >= latin:
            return "arabic"
        tokens = words(text).split()
        derja = sum(token in DERJA_WORDS or bool(DIGIT_IN_WORD.match(token)) for token in tokens)
        french = sum(token in FRENCH_WORDS for token in tokens)
        if derja > french:
            return "derja"
        if french:
            return "french"
    return None


LANGUAGE_HINTS = {
    "arabic": "The candidate writes in Arabic letters: reply in Arabic letters "
              "(Tunisian Derja if they write Derja, else Modern Standard Arabic).",
    "derja": "The candidate writes Tunisian Derja in Latin letters: reply in Derja with Latin letters, not in French.",
    "french": "The candidate writes French: reply in French.",
    None: "Reply in the language and script of the candidate's last message.",
}


def reply_language(messages: list[ChatMessage]) -> str:
    """The instruction telling the model which language to reply in."""
    return LANGUAGE_HINTS[candidate_language(messages)]


# ---------------------------------------------------------------------------
# What the model may send in "updates" (anything that doesn't fit is dropped, field by field)
# ---------------------------------------------------------------------------

def _int_or_none(value: object) -> int | None:
    """A number of months: 24, "24" → 24; anything else ("2 ans", -3, 5000) → None."""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 960 else None


Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Months = Annotated[int | None, BeforeValidator(_int_or_none)]


class ModelSkill(BaseModel):
    name: Short
    level: int | str | None = None


class ModelExperience(BaseModel):
    job_title: Short
    employer: Short | None = None
    months: Months = None


class ModelLanguage(BaseModel):
    code: Short
    level: str | None = None


class ModelUpdates(BaseModel):
    full_name: Short | None = None
    phone: Short | None = None
    governorate: Short | None = None
    education_level: EducationLevel | None = None
    skills: list[ModelSkill] = []
    experiences: list[ModelExperience] = []
    desired_jobs: list[Short] = []
    languages: list[ModelLanguage] = []
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)] | None = None


LIST_FIELDS = {"skills": 20, "experiences": 10, "desired_jobs": 10, "languages": 10}  # field → max items


def _field(name: str, value: object) -> Any:
    """The value checked against ModelUpdates' field, or None when it doesn't fit."""
    try:
        return getattr(ModelUpdates.model_validate({name: value}), name)
    except ValidationError:
        return None


def parse_updates(raw: object) -> ModelUpdates:
    """Keeps every field (and list item) that fits ModelUpdates and drops the rest."""
    if not isinstance(raw, dict):
        return ModelUpdates()
    clean: dict[str, Any] = {}
    for name in ModelUpdates.model_fields:
        value = raw.get(name)
        if value is None:
            continue
        if name not in LIST_FIELDS:
            if (checked := _field(name, value)) is not None:
                clean[name] = checked
            continue
        items = []
        for item in value if isinstance(value, list) else [value]:
            if name == "skills" and isinstance(item, str):
                item = {"name": item}  # "skills": ["soudure"]
            if name == "desired_jobs" and isinstance(item, dict):
                item = item.get("name") or item.get("title") or item.get("job_title")  # [{"name": "vendeur"}]
            if (checked := _field(name, [item])) is not None:
                items += checked
        clean[name] = items[: LIST_FIELDS[name]]
    return ModelUpdates.model_validate(clean)


def _json_failed(exc: groq.APIError) -> bool:
    """Groq's 400 'json_validate_failed': in JSON mode, the model's answer wasn't JSON."""
    error = exc.body.get("error") if isinstance(exc.body, dict) else None
    return isinstance(error, dict) and error.get("code") == "json_validate_failed"


@dataclass
class AssistantAnswer:
    reply: str
    updates: ModelUpdates
    asking: str | None  # the form field the reply asks about (governorate_code, skills...)
    done: bool


def _complete(client: groq.Groq, model: str, chat: list[dict[str, str]]) -> dict[str, Any]:
    """One JSON-mode call to Groq. Returns the answer as a dict with a non-empty "reply", or raises
    AssistantUnavailable with the French message for the candidate."""
    model = model.strip() or DEFAULT_MODEL
    # gpt-oss thinks before answering. "low" saves ~25% of the tokens but often answers Derja in French;
    # "medium" keeps the candidate's language (~1,000 tokens per turn, about 7 turns a minute on the free plan).
    reasoning = {"reasoning_effort": "medium", "include_reasoning": False} if model.startswith("openai/gpt-oss") else {}
    for attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=chat,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_completion_tokens=1024,
                **reasoning,
            )
            break
        except groq.RateLimitError as exc:
            logger.warning("groq rate limit: %s", exc.message)
            raise AssistantUnavailable(status.HTTP_429_TOO_MANY_REQUESTS, BUSY) from exc
        except groq.APIError as exc:  # connection, timeout, bad key, server errors
            if attempt == 0 and _json_failed(exc):
                continue  # the model wrote plain text and Groq refused it: one more try usually works
            logger.warning("groq error %s: %s", type(exc).__name__, exc.message)
            raise AssistantUnavailable(status.HTTP_502_BAD_GATEWAY, SORRY) from exc

    content = completion.choices[0].message.content if completion.choices else None
    try:
        data = json.loads(content or "")
    except json.JSONDecodeError:
        data = None
    reply = data.get("reply") if isinstance(data, dict) else None
    if not isinstance(reply, str) or not reply.strip():
        logger.warning("groq answer is not the expected JSON: %.200r", content)
        raise AssistantUnavailable(status.HTTP_502_BAD_GATEWAY, SORRY)
    return {**data, "reply": reply.strip()[:MAX_REPLY_CHARS]}


def ask_assistant(client: groq.Groq, model: str, messages: list[ChatMessage], draft: AssistantDraft) -> AssistantAnswer:
    """Sends the last few messages and the form's state to Groq; returns its reply and the checked updates."""
    recent = messages[-MAX_MESSAGES:]
    data = _complete(client, model, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": form_state(draft) + "\n" + reply_language(recent)},
        *({"role": message.role, "content": message.content} for message in recent),
    ])
    return AssistantAnswer(
        reply=data["reply"],
        updates=parse_updates(data.get("updates")),
        asking=ASKING.get(data.get("asking")) if isinstance(data.get("asking"), str) else None,
        done=data.get("done") is True,
    )


# ---------------------------------------------------------------------------
# A skill or job that isn't in our lists: stay on it until the candidate fixes it or skips it
# ---------------------------------------------------------------------------

@dataclass
class Unmatched:
    field: str  # the form field it was meant for: "skills" or "desired_occupations"
    name: str


CLARIFY_PROMPT = """You are Assistant Mahara, a friendly Tunisian job-profile assistant.
The candidate named something that isn't in our lists: {missing}.
{lists}
Don't ask the next question yet. In one or two short sentences: name what you didn't find in our list; then suggest up to 3 items of our lists that mean nearly the same thing, naming them, or say that nothing close is in the list; then ask the candidate to write another word (or pick a suggestion) or press "Ignorer" to skip it.
Answer with a JSON object only: {{"reply": "...", "suggestions": ["exact names from our lists"]}}"""

# When the clarifying call fails: a plain message in the candidate's language ({names}: « montage vidéo »).
NOT_FOUND = {
    "arabic": "ما لقيتش {names} في القائمة متاعنا. اكتب كلمة أخرى، ولا اضغط على « Ignorer ».",
    "derja": "Ma l9itech {names} fil lista mte3na. Ekteb kelma okhra, walla enzel 3la « Ignorer ».",
    "french": "Je ne trouve pas {names} dans notre liste. Écrivez un autre mot, ou appuyez sur « Ignorer ».",
}
MAX_SUGGESTIONS = 3


def clarify_unmatched(
    client: groq.Groq,
    model: str,
    messages: list[ChatMessage],
    unmatched: list[Unmatched],
    catalogs: dict[str, list[CatalogSkill]],
) -> tuple[str, list[str]]:
    """A reply that stays on the names we couldn't find, and up to 3 close items of our lists to offer instead.

    `catalogs` holds the lists by form field ("skills", "desired_occupations"). One more Groq call, only when a
    name didn't match; if it fails, a plain "not found" message in the candidate's language is used.
    """
    fields = list(dict.fromkeys(item.field for item in unmatched))
    kind = {"skills": "skill", "desired_occupations": "job"}
    word = {"skills": "compétence", "desired_occupations": "métier"}  # the model reuses these words in its reply
    missing = ", ".join(f'"{item.name}" ({word[item.field]})' for item in unmatched)
    lists = "\n".join(f"Our {kind[field]}s: " + "; ".join(entry.label_fr for entry in catalogs[field]) for field in fields)
    last_user = next((m for m in reversed(messages) if m.role == "user"), None)
    try:
        data = _complete(client, model, [
            {"role": "system", "content": CLARIFY_PROMPT.format(missing=missing, lists=lists)},
            {"role": "system", "content": reply_language(messages)},
            *([{"role": "user", "content": last_user.content}] if last_user else []),
        ])
    except AssistantUnavailable:
        names = ", ".join(f"« {item.name} »" for item in unmatched)
        return NOT_FOUND[candidate_language(messages) or "french"].format(names=names), []

    # Keep only suggestions that really are in our lists, under our label: an alternative label ("cuisinier")
    # or a shortened label ("Bureautique" for "Bureautique (Word, e-mail)") counts too.
    suggestions: list[str] = []
    raw = data.get("suggestions")
    for text in raw if isinstance(raw, list) else []:
        padded = words(text) if isinstance(text, str) else ""
        if len(padded.strip()) < 3:
            continue
        entry = next(
            (e for field in fields for e in catalogs[field] if padded in e.terms or padded in words(e.label_fr)),
            None,
        )
        if entry and entry.label_fr not in suggestions:
            suggestions.append(entry.label_fr)
    return data["reply"], suggestions[:MAX_SUGGESTIONS]


# ---------------------------------------------------------------------------
# Names → codes
# ---------------------------------------------------------------------------

# code: French name, Arabic name, other spellings (Derja in Latin letters, missing accents, common typos).
# The same 24 codes and names as db/schema.sql (a test checks they still match the database).
GOVERNORATES: dict[str, tuple[str, str, list[str]]] = {
    "TN-11": ("Tunis", "تونس", ["tounes", "tunes", "tounis"]),
    "TN-12": ("Ariana", "أريانة", ["aryana", "ariena", "l'ariana"]),
    "TN-13": ("Ben Arous", "بن عروس", ["ben 3arous", "benarous", "ben arouss"]),
    "TN-14": ("Manouba", "منوبة", ["mannouba", "mnouba", "la manouba"]),
    "TN-21": ("Nabeul", "نابل", ["nabel", "nabul"]),
    "TN-22": ("Zaghouan", "زغوان", ["zaghwen", "zaghouen", "zaghwan"]),
    "TN-23": ("Bizerte", "بنزرت", ["benzart", "bizert", "binzart"]),
    "TN-31": ("Béja", "باجة", ["baja", "bja"]),
    "TN-32": ("Jendouba", "جندوبة", ["jandouba", "jenduba"]),
    "TN-33": ("Le Kef", "الكاف", ["kef", "el kef", "lkef", "el kaf"]),
    "TN-34": ("Siliana", "سليانة", ["sliana", "seliana"]),
    "TN-41": ("Kairouan", "القيروان", ["9ayrawen", "9irwen", "9ayrouan", "kairawan", "kairwan", "qairouan", "kerouan"]),
    "TN-42": ("Kasserine", "القصرين", ["kasrine", "gasrine", "kassrine", "9asrine"]),
    "TN-43": ("Sidi Bouzid", "سيدي بوزيد", ["sidi bouzaid", "sidi bouzeid", "sidibouzid"]),
    "TN-51": ("Sousse", "سوسة", ["sousa", "soussa", "souse", "susa"]),
    "TN-52": ("Monastir", "المنستير", ["mestir", "mnastir"]),
    "TN-53": ("Mahdia", "المهدية", ["mehdia", "mahdiya", "el mahdia"]),
    "TN-61": ("Sfax", "صفاقس", ["sfaks", "sfakes", "sfa9es", "sfaqes"]),
    "TN-71": ("Gafsa", "قفصة", ["9afsa", "gafssa", "gfsa"]),
    "TN-72": ("Tozeur", "توزر", ["touzer", "tozer", "twezer"]),
    "TN-73": ("Kébili", "قبلي", ["gbeli", "9bili", "gebili", "kbili"]),
    "TN-81": ("Gabès", "قابس", ["9abes", "qabes", "gabis"]),
    "TN-82": ("Médenine", "مدنين", ["mednine", "mednin", "madanin"]),
    "TN-83": ("Tataouine", "تطاوين", ["tatouine", "tatawin", "tataouin", "tatawine"]),
}
GOVERNORATE_NAMES = {code: name_fr for code, (name_fr, _, _) in GOVERNORATES.items()}

ARABIC_MARKS = re.compile(r"[ً-ٰٟـ]")  # short vowels and the tatweel


def any_words(text: str) -> str:
    """Like words(), for Latin and Arabic letters: ' sfax ', ' صفاقس ' ('al-' removed, ة read as ه)."""
    folded = ARABIC_MARKS.sub("", fold(text)).replace("ة", "ه").replace("ى", "ي")
    tokens = re.findall(r"[a-z0-9]+|[ء-ي]+", folded)
    tokens = [token[2:] if token.startswith("ال") and len(token) > 4 else token for token in tokens]
    return " " + " ".join(tokens) + " "


GOVERNORATE_TERMS = [
    (code, any_words(term))
    for code, (name_fr, name_ar, other) in GOVERNORATES.items()
    for term in [name_fr, name_ar, *other]
]


def find_governorate(text: str) -> str | None:
    """'Sousse', 'Sousa', 'سوسة', 'men Sousse' → 'TN-51'. The longest name found wins."""
    padded = any_words(text)
    found = [(len(term), code) for code, term in GOVERNORATE_TERMS if term in padded]
    return max(found)[1] if found else None


# Checked in this order: "très bien" is 4 before "bien" is 3.
SKILL_LEVEL_WORDS = [
    (4, ["barcha", "barsha", "yesser", "expert", "experte", "tres bien", "tres bon", "tres bonne", "excellent",
         "excellente", "parfait", "parfaitement", "maitrise", "professionnel", "برشا", "ياسر", "خبير", "ممتاز",
         "محترف"]),
    (1, ["chwaya", "chwaia", "chwaiya", "chouaya", "chouia", "chwia", "shwaya", "un peu", "peu", "debutant",
         "debutante", "notions", "شوية", "قليل", "مبتدئ"]),
    (3, ["behi", "bahi", "mli7", "mlih", "bien", "bon", "bonne", "pas mal", "avance", "avancee", "confirme",
         "confirmee", "باهي", "مليح", "جيد", "متقدم"]),
    (2, ["normal", "normale", "moyen", "moyenne", "intermediaire", "3adi", "3ady", "عادي", "متوسط"]),
]
SKILL_LEVEL_TERMS = [(level, any_words(term)) for level, terms in SKILL_LEVEL_WORDS for term in terms]
# "mouch barcha" (not much), "pas très bien": a good level with a negation is a low one ("pas mal" isn't).
NEGATIONS = [any_words(term) for term in ["mouch", "moch", "mech", "mich", "pas", "مش", "موش"]]
DEFAULT_SKILL_LEVEL = 2  # the form's default for a new skill


def skill_level(value: int | str | None) -> int:
    """1-4 from a number or the candidate's words ('chwaya' 1, 'moyen' 2, 'behi' 3, 'barcha' 4); else 2."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value if 1 <= value <= 4 else DEFAULT_SKILL_LEVEL
    if isinstance(value, str):
        if value.strip() in {"1", "2", "3", "4"}:
            return int(value.strip())
        padded = any_words(value)
        for level, term in SKILL_LEVEL_TERMS:
            if term in padded:
                negated = level >= 3 and term != " pas mal " and any(word in padded for word in NEGATIONS)
                return 1 if negated else level
    return DEFAULT_SKILL_LEVEL


LANGUAGE_NAMES = {  # when the model writes a name instead of the ISO code
    "arabe": "ar", "arabic": "ar", "derja": "ar", "darija": "ar", "tunisien": "ar", "3arbi": "ar",
    "francais": "fr", "french": "fr", "fransi": "fr", "anglais": "en", "english": "en", "angliz": "en",
    "allemand": "de", "german": "de", "italien": "it", "italian": "it", "espagnol": "es", "spanish": "es",
    "turc": "tr", "chinois": "zh",
}


def _language(item: ModelLanguage) -> LanguageOut | None:
    code = fold(item.code).strip()
    code = code if re.fullmatch(r"[a-z]{2,3}", code) else LANGUAGE_NAMES.get(code)
    if not code:
        return None
    level = (item.level or "").strip().lower()
    return LanguageOut(code=code, level=level if level in LANGUAGE_LEVELS else "intermediate")


def match_catalog(name: str, catalog: list[CatalogSkill]) -> list[CatalogSkill]:
    """Catalog entries named in `name`, with the CV import's matching ('cuisine tunisienne' → Cuisine);
    else the first one whose label contains it ('informatique' → 'informatique de base')."""
    by_code = {entry.code: entry for entry in catalog}
    found = [by_code[skill.code] for skill in find_skills(name, catalog)]
    if found:
        return found
    padded = words(name)
    if len(padded.strip()) < 4:
        return []
    return [entry for entry in catalog if any(padded in term for term in entry.terms)][:1]


def load_occupations(db: Session) -> list[CatalogSkill]:
    """The occupations list in one query, with each part of 'Soudeur / Soudeuse' as a search term."""
    occupations = []
    for code, title in db.execute(select(Occupation.code, Occupation.title_fr)):
        terms = {words(term) for term in [title, *title.split("/")]}
        occupations.append(CatalogSkill(code, title, [term for term in terms if len(term.strip()) >= 2]))
    return occupations


def resolve_updates(
    updates: ModelUpdates,
    load_skills: Callable[[], list[CatalogSkill]],
    load_occupations: Callable[[], list[CatalogSkill]],
) -> tuple[AssistantUpdates, list[Unmatched]]:
    """The model's updates in the form's shape, with codes. Catalogs are only read when needed (one query each).

    Returns the updates and the skill and job names that match nothing in our lists.
    """
    out = AssistantUpdates(
        full_name=updates.full_name,
        # A Tunisian number written like the CV import does ('22 345 678'); anything else is dropped.
        phone=(find_phone(updates.phone) or None) if updates.phone else None,
        governorate_code=find_governorate(updates.governorate) if updates.governorate else None,
        education_level=updates.education_level,
        summary=updates.summary,
    )
    unmatched: list[Unmatched] = []

    if updates.skills:
        catalog = load_skills()
        skills: dict[str, CvSkill] = {}
        for item in updates.skills:
            found = match_catalog(item.name, catalog)
            if not found:
                unmatched.append(Unmatched("skills", item.name))
            for entry in found:
                skills.setdefault(entry.code, CvSkill(
                    code=entry.code, label_fr=entry.label_fr, level=skill_level(item.level), source="self_declared",
                ))
        out.skills = list(skills.values()) or None

    if updates.experiences:
        out.experiences = [
            CvExperience(
                job_title_raw=item.job_title,
                employer_name=item.employer or "",
                duration_months="" if item.months is None else str(item.months),
            )
            for item in updates.experiences
        ]

    if updates.desired_jobs:
        catalog = load_occupations()
        jobs: dict[str, OccupationOut] = {}
        for name in updates.desired_jobs:
            found = match_catalog(name, catalog)[:1]  # one job named → one occupation
            if not found:
                unmatched.append(Unmatched("desired_occupations", name))
            for entry in found:
                jobs.setdefault(entry.code, OccupationOut(code=entry.code, title_fr=entry.label_fr))
        out.desired_occupations = list(jobs.values()) or None

    languages = {language.code: language for item in updates.languages if (language := _language(item))}
    out.languages = list(languages.values()) or None

    return out, list({(item.field, fold(item.name)): item for item in unmatched}.values())


def assistant_turn(
    client: groq.Groq,
    model: str,
    body: AssistantChatIn,
    load_skills: Callable[[], list[CatalogSkill]],
    load_occupations: Callable[[], list[CatalogSkill]],
) -> AssistantChatOut:
    """One turn: the model's reply and updates with codes. When a skill or job isn't in our lists, the reply is
    replaced by one that stays on it (suggestions from our lists, or "Ignorer"), so the chat doesn't move on."""
    skills, occupations = cache(load_skills), cache(load_occupations)  # read each list once at most
    answer = ask_assistant(client, model, body.messages, body.draft)
    updates, unmatched = resolve_updates(answer.updates, skills, occupations)
    if not unmatched:
        return AssistantChatOut(
            reply=answer.reply, updates=updates, unmatched=[], suggestions=[], asking=answer.asking, done=answer.done,
        )
    loaders = {"skills": skills, "desired_occupations": occupations}
    catalogs = {field: loaders[field]() for field in {item.field for item in unmatched}}  # already read above
    reply, suggestions = clarify_unmatched(client, model, body.messages, unmatched, catalogs)
    return AssistantChatOut(
        reply=reply,
        updates=updates,
        unmatched=[item.name for item in unmatched],
        suggestions=suggestions,
        asking=unmatched[0].field,
        done=False,
    )
