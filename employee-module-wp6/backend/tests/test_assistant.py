import json
import uuid
from types import SimpleNamespace

import groq
import httpx
import pytest
from sqlalchemy import func, select

from app.auth import get_token_claims
from app.config import Settings, get_settings
from app.db import get_db
from app.main import app
from app.models import Candidate, Governorate, Occupation, Skill
from app.services.assistant import (
    BUSY,
    GOVERNORATES,
    NO_KEY,
    SORRY,
    find_governorate,
    get_groq_client,
    parse_updates,
    resolve_updates,
    skill_level,
)
from app.services.cv_import import CatalogSkill, words

URL = "/api/v1/me/assistant/chat"
GREETING = (
    "Ahla ! Je vais vous aider à compléter votre profil. Vous pouvez répondre en français ou en derja. "
    "Comment vous appelez-vous ?"
)


class FakeGroq:
    """Stands in for groq.Groq. Each call gives the next outcome (the last one repeats):
    a string is the model's answer, an exception is raised."""

    def __init__(self, *outcomes: str | Exception | None):
        self.outcomes, self.calls = outcomes, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes[min(len(self.calls), len(self.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))])


def answer(reply: str, updates: dict | None = None, done: bool = False, asking: object = None) -> str:
    return json.dumps(
        {"reply": reply, "updates": updates or {}, "asking": asking, "done": done}, ensure_ascii=False,
    )


def status_error(cls, status_code: int, body: object = None):
    response = httpx.Response(status_code, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat"))
    return cls("error", response=response, body=body)


JSON_FAILED = status_error(groq.BadRequestError, 400, {"error": {
    "message": "Failed to generate JSON.", "code": "json_validate_failed", "failed_generation": "Merci !",
}})


@pytest.fixture
def no_db(client):
    """Signed in, without a database: a test fails if the endpoint tries to read one."""
    app.dependency_overrides[get_token_claims] = lambda: {"email": "amine@example.tn"}
    app.dependency_overrides[get_db] = lambda: None


def use(fake: FakeGroq) -> FakeGroq:
    app.dependency_overrides[get_groq_client] = lambda: fake
    return fake


def chat(client, *user_messages: str, draft: dict | None = None):
    messages = [{"role": "assistant", "content": GREETING}]
    for text in user_messages:
        messages.append({"role": "user", "content": text})
    return client.post(URL, json={"messages": messages, "draft": draft or {}})


# ---------------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def catalog(db):
    """Test-only skills and occupation, with labels the seed can't have."""
    tag = uuid.uuid4().hex[:6].upper()
    db.add_all([
        Skill(code=f"SK-T{tag}1", label_fr=f"Zqx{tag} Ferronnerie", skill_type="hard",
              alt_labels=[f"zqx{tag} ferronnier"], status="validated"),
        Skill(code=f"SK-T{tag}2", label_fr=f"Zqx{tag} Marqueterie", skill_type="hard", status="validated"),
        Occupation(code=f"OC-T{tag}1", title_fr=f"Zqx{tag} Ferronnier / Zqx{tag} Ferronnière"),
    ])
    db.flush()
    return tag


def test_french_answer_fills_the_form(client, signed_in, db, catalog):
    tag = catalog
    fake = use(FakeGroq(answer(
        "Merci Amira ! Quel est votre niveau d'études ?",
        {
            "full_name": "Amira Ben Salah",
            "phone": "+216 22345678",
            "governorate": "Sfax",
            "education_level": "vocational_bts",
            "skills": [
                {"name": f"zqx{tag} ferronnier", "level": "très bien"},
                {"name": f"Zqx{tag} marqueterie", "level": 2},
            ],
            "experiences": [{"job_title": "Soudeuse", "employer": "SMS", "months": 36}],
            "desired_jobs": [f"zqx{tag} ferronnière"],
            "languages": [{"code": "fr", "level": "fluent"}],
            "consent": True,  # not a form field the assistant may fill: dropped
        },
    )))
    history = [{"role": "user" if i % 2 else "assistant", "content": f"message {i}"} for i in range(11)]
    history.append({"role": "user", "content": "Je m'appelle Amira Ben Salah, j'habite à Sfax, 22 345 678."})

    response = client.post(URL, json={
        "messages": history,
        "draft": {"full_name": "Amira", "phone": "20 111 222", "governorate_code": "", "consent": False},
    })

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Merci Amira ! Quel est votre niveau d'études ?"
    assert body["done"] is False
    updates = body["updates"]
    assert updates["full_name"] == "Amira Ben Salah"
    assert updates["phone"] == "+216 22 345 678"
    assert updates["governorate_code"] == "TN-61"
    assert updates["education_level"] == "vocational_bts"
    assert [(s["code"], s["level"], s["source"]) for s in updates["skills"]] == [
        (f"SK-T{tag}1", 4, "self_declared"), (f"SK-T{tag}2", 2, "self_declared"),
    ]
    assert updates["experiences"] == [{
        "job_title_raw": "Soudeuse", "employer_name": "SMS", "start_date": "", "end_date": "",
        "duration_months": "36", "description": "",
    }]
    assert updates["desired_occupations"] == [
        {"code": f"OC-T{tag}1", "title_fr": f"Zqx{tag} Ferronnier / Zqx{tag} Ferronnière"},
    ]
    assert updates["languages"] == [{"code": "fr", "level": "fluent"}]
    assert updates["summary"] is None
    assert "consent" not in updates
    assert body["unmatched"] == [] and body["suggestions"] == []

    # What went to Groq: JSON mode, the prompt, the form's state (without the phone number), the last 8 messages.
    (call,) = fake.calls
    assert call["model"] == get_settings().groq_model
    assert call["response_format"] == {"type": "json_object"}
    system, state, *messages = call["messages"]
    assert "Assistant Mahara" in system["content"] and "Derja" in system["content"]
    assert '"full_name": "Amira"' in state["content"] and "20 111 222" not in state["content"]
    assert "Still empty: governorate" in state["content"]
    assert messages == history[-8:]
    # Nothing saved.
    assert db.scalar(select(func.count()).select_from(Candidate).where(Candidate.user_id == signed_in.id)) == 0


def test_derja_answer(client, no_db):
    fake = use(FakeGroq(answer(
        "Ahla bik Amine! Chnowa noumrou telifounek?",
        {"full_name": "Amine", "governorate": "Sousa"},
        asking="phone",
    )))

    response = chat(client, "esmi Amine, men Sousse")

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Ahla bik Amine! Chnowa noumrou telifounek?",
        "updates": {
            "full_name": "Amine", "phone": None, "governorate_code": "TN-51", "education_level": None,
            "skills": None, "experiences": None, "desired_occupations": None, "languages": None, "summary": None,
        },
        "unmatched": [],
        "suggestions": [],
        "asking": "phone",
        "done": False,
    }
    assert fake.calls[0]["messages"][-1] == {"role": "user", "content": "esmi Amine, men Sousse"}


@pytest.mark.parametrize(("asking", "field"), [
    ("governorate", "governorate_code"),  # the model's names → the form's fields
    ("skills", "skills"),
    ("desired_jobs", "desired_occupations"),
    ("summary", "summary"),
    ("consent", None),  # not a field the assistant asks about
    ("SKILLS", None),
    (3, None),
    (None, None),
])
def test_asking_names_the_form_field(client, no_db, asking, field):
    use(FakeGroq(answer("?", asking=asking)))
    assert chat(client, "Amine").json()["asking"] == field


def test_done(client, no_db):
    use(FakeGroq(answer("Yezzi, verifi el formulaire w enzel 3la « Enregistrer ».", {}, done=True)))
    response = chat(client, "safa, kammalt")
    assert response.status_code == 200
    assert response.json()["done"] is True
    assert response.json()["asking"] is None


@pytest.mark.parametrize("content", [
    "Bonjour ! Quel est votre nom ?",  # plain text instead of JSON
    '{"reply": "Merci", "updates": {',  # cut off
    '["reply"]',  # JSON, but not an object
    '{"updates": {"full_name": "Amine"}}',  # no reply
    None,
])
def test_invalid_json_from_the_model(client, no_db, content):
    use(FakeGroq(content))
    response = chat(client, "Amine")
    assert response.status_code == 502
    assert response.json() == {"detail": SORRY}


def test_invalid_updates_are_dropped(client, no_db):
    use(FakeGroq(answer("D'accord.", {
        "full_name": "",
        "phone": "123",
        "governorate": "Paris",
        "education_level": "phd",
        "experiences": [{"employer": "STEG"}, {"job_title": "Serveur", "months": "deux ans"}],
        "languages": [{"code": "Français", "level": "super"}, {"code": "??"}],
        "summary": "x" * 600,
    })))

    updates = chat(client, "...").json()["updates"]

    assert updates["full_name"] is None
    assert updates["phone"] is None
    assert updates["governorate_code"] is None
    assert updates["education_level"] is None
    assert [(e["job_title_raw"], e["duration_months"]) for e in updates["experiences"]] == [("Serveur", "")]
    assert updates["languages"] == [{"code": "fr", "level": "intermediate"}]
    assert updates["summary"] is None


def test_missing_key(client, no_db):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, groq_api_key=None)
    response = chat(client, "Amine")
    assert response.status_code == 503
    assert response.json() == {"detail": NO_KEY}


def test_rate_limit(client, no_db):
    use(FakeGroq(status_error(groq.RateLimitError, 429)))
    response = chat(client, "Amine")
    assert response.status_code == 429
    assert response.json() == {"detail": BUSY}
    assert "réessayez dans quelques secondes" in BUSY


@pytest.mark.parametrize("error", [
    status_error(groq.InternalServerError, 503),
    status_error(groq.AuthenticationError, 401),
    status_error(groq.BadRequestError, 400),
    groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com")),
])
def test_other_groq_errors(client, no_db, error):
    fake = use(FakeGroq(error))
    response = chat(client, "Amine")
    assert response.status_code == 502
    assert response.json() == {"detail": SORRY}
    assert len(fake.calls) == 1


def test_json_mode_failure_is_retried_once(client, no_db):
    fake = use(FakeGroq(JSON_FAILED, answer("Merci Amine !", {"full_name": "Amine"})))
    response = chat(client, "Amine")
    assert response.status_code == 200
    assert response.json()["reply"] == "Merci Amine !"
    assert len(fake.calls) == 2

    fake = use(FakeGroq(JSON_FAILED))
    response = chat(client, "Amine")
    assert response.status_code == 502
    assert response.json() == {"detail": SORRY}
    assert len(fake.calls) == 2


@pytest.mark.parametrize(("messages", "language"), [
    (["esmi Amine, men Sousse"], "Derja"),
    (["na3ref nsaoudi barcha"], "Derja"),
    (["Je m'appelle Amine et j'habite à Sousse"], "French"),
    (["إسمي أمين من سوسة"], "Arabic letters"),
    (["esmi Amine", "22 345 678"], "Derja"),  # no words: the previous message decides
])
def test_reply_language_hint(client, no_db, messages, language):
    fake = use(FakeGroq(answer("...")))
    chat(client, *messages)
    state = fake.calls[0]["messages"][1]["content"]
    assert language in state.splitlines()[-1]


def test_bad_request_body(client, no_db):
    use(FakeGroq(answer("?")))
    assert client.post(URL, json={"messages": [], "draft": {}}).status_code == 422
    assert client.post(URL, json={"messages": [{"role": "system", "content": "x"}]}).status_code == 422


def test_requires_login(client, signed_out):
    response = client.post(URL, json={"messages": [{"role": "user", "content": "Amine"}], "draft": {}})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Matching (no database)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("text", "code"), [
    ("Sousse", "TN-51"), ("Sousa", "TN-51"), ("سوسة", "TN-51"),
    ("Sfax", "TN-61"), ("Sfaks", "TN-61"), ("صفاقس", "TN-61"),
    ("Kairouan", "TN-41"), ("9ayrawen", "TN-41"), ("القيروان", "TN-41"),
    ("Gabès", "TN-81"), ("gabes", "TN-81"), ("men el Kef", "TN-33"), ("Sidi Bouzid", "TN-43"),
    ("Tunisie", None), ("Paris", None),
])
def test_find_governorate(text, code):
    assert find_governorate(text) == code


@pytest.mark.parametrize(("value", "level"), [
    ("chwaya", 1), ("un peu", 1), ("normal", 2), ("moyen", 2), ("behi", 3), ("bien", 3),
    ("barcha", 4), ("expert", 4), ("très bien", 4), ("mouch barcha", 1), ("pas mal", 3),
    ("باهي", 3), ("برشا", 4), (3, 3), ("4", 4), (7, 2), (None, 2), ("?", 2),
])
def test_skill_level(value, level):
    assert skill_level(value) == level


def entries(*items: tuple[str, str, list[str]]) -> list[CatalogSkill]:
    return [CatalogSkill(code, label, [words(term) for term in [label, *alt]]) for code, label, alt in items]


SKILLS = entries(
    ("SK-1", "Cuisine", ["cuisinier"]),
    ("SK-2", "Bureautique (Word, e-mail)", ["word", "informatique de base"]),
    ("SK-3", "Vente", ["vendeur"]),
    ("SK-4", "Caisse", ["caissier"]),
)
JOBS = [
    CatalogSkill("OC-1", "Chauffeur-livreur / Chauffeuse-livreuse",
                 [words("Chauffeur-livreur"), words("Chauffeuse-livreuse")]),
    CatalogSkill("OC-2", "Vendeur / Vendeuse en magasin", [words("Vendeur"), words("Vendeuse en magasin")]),
]


def test_resolve_updates_matches_names_to_codes():
    updates = parse_updates({
        "skills": [
            {"name": "cuisine tunisienne", "level": "behi"},  # a catalog label inside the name
            {"name": "informatique", "level": 1},  # the name inside a catalog label
            {"name": "vente et caisse", "level": "barcha"},  # two skills at once
            {"name": "Photoshop"},
        ],
        "desired_jobs": ["chauffeur", "vendeuse", "astronaute"],
    })

    out, unmatched = resolve_updates(updates, lambda: SKILLS, lambda: JOBS)

    assert [(s.code, s.level) for s in out.skills] == [("SK-1", 3), ("SK-2", 1), ("SK-3", 4), ("SK-4", 4)]
    assert [job.code for job in out.desired_occupations] == ["OC-1", "OC-2"]
    assert [(item.field, item.name) for item in unmatched] == [
        ("skills", "Photoshop"), ("desired_occupations", "astronaute"),
    ]


def test_resolve_updates_reads_catalogs_only_when_needed():
    def fail():
        raise AssertionError("catalog read")

    out, unmatched = resolve_updates(parse_updates({"full_name": "Amine"}), fail, fail)
    assert out.full_name == "Amine" and unmatched == []


# ---------------------------------------------------------------------------
# A skill or job that isn't in our lists: the chat stays on it
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_catalogs(monkeypatch):
    """The endpoint reads SKILLS and JOBS instead of the database."""
    import app.routers.assistant as router

    monkeypatch.setattr(router, "load_skills", lambda _db: SKILLS)
    monkeypatch.setattr(router, "load_occupations", lambda _db: JOBS)


FIRST = answer(
    "Très bien ! Où avez-vous déjà travaillé ?",  # the model moved on: this reply must not reach the candidate
    {"skills": [{"name": "cuisine", "level": 3}, {"name": "montage vidéo", "level": 4}]},
    asking="experiences",
    done=True,
)


def test_unmatched_skill_keeps_the_chat_on_it(client, no_db, fake_catalogs):
    clarify = json.dumps({
        "reply": "Je ne trouve pas « montage vidéo ». Proche : Bureautique. Choisissez, écrivez un autre mot, "
                 "ou appuyez sur « Ignorer ».",
        "suggestions": ["Bureautique", "Astrophysique", "cuisinier", "Bureautique (Word, e-mail)", 7],
    })
    fake = use(FakeGroq(FIRST, clarify))

    response = chat(client, "Je sais bien cuisiner et je fais du montage vidéo")

    assert response.status_code == 200
    body = response.json()
    assert body["reply"].startswith("Je ne trouve pas « montage vidéo »")
    assert body["unmatched"] == ["montage vidéo"]
    # Only names from our list, under our label; "Astrophysique" and the number are dropped.
    assert body["suggestions"] == ["Bureautique (Word, e-mail)", "Cuisine"]
    assert body["asking"] == "skills"
    assert body["done"] is False
    assert [(s["code"], s["level"]) for s in body["updates"]["skills"]] == [("SK-1", 3)]  # the match is kept
    # The second call names what's missing and gives our list, and answers the candidate's last message.
    assert len(fake.calls) == 2
    system, language, last = fake.calls[1]["messages"]
    assert '"montage vidéo" (compétence)' in system["content"] and "Bureautique (Word, e-mail)" in system["content"]
    assert "Our jobs" not in system["content"]
    assert "French" in language["content"]
    assert last == {"role": "user", "content": "Je sais bien cuisiner et je fais du montage vidéo"}


@pytest.mark.parametrize(("message", "start"), [
    ("Je fais du montage vidéo", "Je ne trouve pas « montage vidéo »"),
    ("na3ref na3mel montage vidéo barcha", "Ma l9itech « montage vidéo »"),
    ("نعرف نعمل مونتاج فيديو", "ما لقيتش « montage vidéo »"),
])
def test_unmatched_without_a_second_answer(client, no_db, fake_catalogs, message, start):
    use(FakeGroq(FIRST, status_error(groq.RateLimitError, 429)))
    body = chat(client, message).json()
    assert body["reply"].startswith(start) and "Ignorer" in body["reply"]
    assert body["suggestions"] == []
    assert body["asking"] == "skills" and body["done"] is False


def test_unmatched_job(client, no_db, fake_catalogs):
    fake = use(FakeGroq(
        answer("Et les langues ?", {"desired_jobs": ["astronaute"]}, asking="languages"),
        json.dumps({"reply": "Pas d'astronaute chez nous. Vendeur ?", "suggestions": ["Vendeur"]}),
    ))
    body = chat(client, "Je veux être astronaute").json()
    assert body["suggestions"] == ["Vendeur / Vendeuse en magasin"]
    assert body["asking"] == "desired_occupations"
    assert "Our jobs" in fake.calls[1]["messages"][0]["content"]


def test_governorates_match_the_database(db):
    rows = {code: (name_fr, name_ar) for code, name_fr, name_ar in db.execute(
        select(Governorate.code, Governorate.name_fr, Governorate.name_ar)
    )}
    assert rows == {code: (name_fr, name_ar) for code, (name_fr, name_ar, _) in GOVERNORATES.items()}
