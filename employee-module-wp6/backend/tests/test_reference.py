import uuid

import pytest

from app.models import Occupation, Skill


@pytest.fixture
def catalog(db):
    """Test-only skills and occupations; their codes can't collide with the seed or the team's list."""
    tag = uuid.uuid4().hex[:6].upper()
    db.add_all([
        Skill(code=f"SK-T{tag}1", label_fr=f"Zqx{tag} Électronique", skill_type="hard",
              alt_labels=[f"zqx{tag} electronique"], status="validated"),
        Skill(code=f"SK-T{tag}2", label_fr=f"Zqx{tag} Ancienne compétence", skill_type="hard", status="deprecated"),
        Occupation(code=f"OC-T{tag}1", title_fr=f"Zqx{tag} Technicien"),
    ])
    db.flush()
    return tag


def test_governorates_lists_all_24(client, signed_in):
    response = client.get("/api/v1/reference/governorates")
    assert response.status_code == 200
    governorates = response.json()
    assert len(governorates) == 24
    assert governorates[0] == {"code": "TN-11", "name_fr": "Tunis", "name_ar": "تونس"}


def test_skills_search_matches_accent_free_alt_label(client, signed_in, catalog):
    response = client.get("/api/v1/reference/skills", params={"q": f"zqx{catalog} electro"})
    assert response.status_code == 200
    assert response.json() == [
        {"code": f"SK-T{catalog}1", "label_fr": f"Zqx{catalog} Électronique", "skill_type": "hard"}
    ]


def test_skills_search_hides_deprecated(client, signed_in, catalog):
    response = client.get("/api/v1/reference/skills", params={"q": f"zqx{catalog}"})
    assert [skill["code"] for skill in response.json()] == [f"SK-T{catalog}1"]


def test_skills_search_returns_at_most_20(client, signed_in, catalog):
    response = client.get("/api/v1/reference/skills")
    assert response.status_code == 200
    assert len(response.json()) <= 20


def test_skills_search_treats_percent_literally(client, signed_in, catalog):
    response = client.get("/api/v1/reference/skills", params={"q": "%"})
    assert response.status_code == 200
    assert response.json() == []


def test_occupations_search(client, signed_in, catalog):
    response = client.get("/api/v1/reference/occupations", params={"q": f"ZQX{catalog} tech"})
    assert response.status_code == 200
    assert response.json() == [{"code": f"OC-T{catalog}1", "title_fr": f"Zqx{catalog} Technicien"}]


@pytest.mark.parametrize("path", ["governorates", "skills", "occupations"])
def test_reference_requires_login(client, signed_out, path):
    response = client.get(f"/api/v1/reference/{path}")
    assert response.status_code == 401
