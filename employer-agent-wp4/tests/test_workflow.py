import asyncio
import json
from types import SimpleNamespace

from mahara_data.db.models.taxonomy import Skill

from employer_agent_wp4.workflow import generate_offer


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    async def complete_chat(self, messages, **kwargs):
        self.calls += 1
        return json.dumps(self.response)


class FakeQuery:
    def __init__(self, skills):
        self.skills = skills

    def filter(self, criterion):
        return self

    def all(self):
        return self.skills


class FakeDatabase:
    def __init__(self, skills):
        self.skills = skills

    def query(self, model):
        return FakeQuery(self.skills)


def offer_payload(skill_code="SK-0001"):
    return {
        "title": "Vendeur en magasin",
        "description": "Accueillir les clients et organiser les produits en rayon.",
        "occupation_code": None,
        "sector_code": None,
        "contract_type": "cdd",
        "work_mode": "on_site",
        "location": {"governorate_code": "TN-11", "delegation": "Tunis"},
        "positions_count": 2,
        "min_years_experience": 0,
        "education_level_min": None,
        "salary": None,
        "skills": [{"skill_code": skill_code, "requirement": "required", "min_level": 1}],
        "languages_required": [],
        "status": "draft",
        "source": "employer_form",
    }


def complete_state():
    return {
        "answers": {
            "title": "Vendeur en magasin",
            "responsibilities": "Accueillir les clients et organiser les produits en rayon.",
            "location": "Tunis",
            "contract_type": "CDD",
            "required_skills": "Accueil client",
        },
        "skipped": ["salary"],
    }


def validated_skill(code="SK-0001"):
    return SimpleNamespace(code=code, label_fr="Accueil client", label_derja="ist9bel el clients")


def test_incomplete_answers_are_returned_without_calling_llm():
    client = FakeLLM(offer_payload())
    state = {"answers": {"title": "Vendeur"}, "skipped": []}

    result, missing = asyncio.run(
        generate_offer(client, FakeDatabase([validated_skill()]), state, "employer-id", Skill)
    )

    assert result is None
    assert "responsibilities" in missing
    assert client.calls == 0


def test_generation_returns_wp1_validated_offer_with_employer_id():
    client = FakeLLM(offer_payload())

    result, missing = asyncio.run(
        generate_offer(client, FakeDatabase([validated_skill()]), complete_state(), "11111111-1111-4111-8111-111111111111", Skill)
    )

    assert missing == []
    assert result["title"] == "Vendeur en magasin"
    assert result["employer_id"] == "11111111-1111-4111-8111-111111111111"
    assert result["skills"][0]["skill_code"] == "SK-0001"


def test_generation_rejects_skill_codes_absent_from_validated_taxonomy():
    client = FakeLLM(offer_payload("SK-FAKE"))

    result, missing = asyncio.run(
        generate_offer(
            client,
            FakeDatabase([validated_skill()]),
            complete_state(),
            "11111111-1111-4111-8111-111111111111",
            Skill,
        )
    )

    assert result is None
    assert missing == ["unrecognized_skill_codes"]


def test_generation_stays_incomplete_when_validated_taxonomy_is_empty():
    client = FakeLLM(offer_payload())

    result, missing = asyncio.run(
        generate_offer(client, FakeDatabase([]), complete_state(), "employer-id", Skill)
    )

    assert result is None
    assert missing == ["validated_skill_taxonomy"]
    assert client.calls == 0