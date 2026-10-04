import io
import uuid
from pathlib import Path

import pytest
from pypdf import PdfWriter
from sqlalchemy import func, select

from app.auth import get_token_claims
from app.db import get_db
from app.main import app
from app.models import Candidate, Skill
from app.services.cv_import import (
    KERNING_SPLIT,
    MAX_CV_BYTES,
    UNREADABLE,
    CatalogSkill,
    build_draft,
    find_dates,
    find_phone,
    read_text,
    words,
)

URL = "/api/v1/me/cv"
FIXTURES = Path(__file__).parent / "fixtures"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def catalog(*skills: tuple[str, str, list[str]]) -> list[CatalogSkill]:
    return [CatalogSkill(code, label, [words(term) for term in [label, *alt]]) for code, label, alt in skills]


CATALOG = catalog(
    ("SK-1", "Soudure", ["soudeur", "soudage"]),
    ("SK-2", "Excel", ["microsoft excel"]),
    ("SK-3", "Français", ["francais"]),
    ("SK-4", "Vente", ["vente en magasin"]),
    ("SK-5", "Plomberie", ["plombier"]),
)


def sample(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def upload(client, name: str, data: bytes, content_type: str = "application/pdf"):
    return client.post(URL, files={"file": (name, data, content_type)})


def blank_pdf() -> bytes:
    """A PDF with one empty page, like a scanned CV: no text to read."""
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Parsing (no database)
# ---------------------------------------------------------------------------

def test_sample_pdf_parses():
    result = build_draft(read_text("pdf", sample("sample_cv.pdf")), CATALOG)
    draft = result.draft

    assert draft.full_name == "Amira Ben Salah"
    assert draft.email == "amira.bensalah@example.tn"
    assert draft.phone == "+216 22 345 678"
    assert [(s.code, s.level, s.source) for s in draft.skills] == [
        ("SK-1", 2, "cv"), ("SK-2", 2, "cv"), ("SK-3", 2, "cv"),
    ]
    assert draft.education_level == "vocational_bts"
    assert [(e.level, e.field_of_study, e.institution, e.graduation_year) for e in draft.educations] == [
        ("vocational_bts", "Construction métallique", "ISET Sfax", 2017),
        ("baccalaureate", "Technique", "Lycée Hédi Chaker", 2015),
    ]
    first, second = draft.experiences
    assert (first.job_title_raw, first.employer_name) == ("Soudeuse", "Société Métallurgique du Sud, Sfax")
    assert (first.start_date, first.end_date) == ("2019-03-01", "")  # "aujourd'hui": still in the job
    assert first.description.startswith("Soudure à l'arc")
    assert (second.job_title_raw, second.employer_name) == ("Aide-soudeuse", "Atelier Ben Ali")
    assert (second.start_date, second.end_date) == ("2017-01-01", "2019-12-01")
    assert "Lecture de plans" in result.unmatched_words
    assert "Soudure" not in result.unmatched_words


def test_sample_docx_parses():
    result = build_draft(read_text("docx", sample("sample_cv.docx")), CATALOG)
    draft = result.draft

    assert draft.full_name == "Mohamed Trabelsi"  # "Curriculum Vitae" on the first line is skipped
    assert draft.email == "mohamed.trabelsi@example.tn"  # read from a table, lower-cased
    assert draft.phone == "98 765 432"
    assert [s.code for s in draft.skills] == ["SK-4", "SK-2", "SK-3"]
    assert draft.education_level == "licence"
    assert draft.educations[0].field_of_study == "Gestion commerciale"
    assert draft.educations[0].institution == "ISG Tunis"
    first, second = draft.experiences
    assert (first.job_title_raw, first.employer_name) == ("Vendeur", "Carrefour La Marsa")
    assert (first.start_date, first.end_date) == ("2021-01-01", "2023-12-01")
    assert first.description == "Conseil et vente en magasin, encaissement\nConseil aux clients"
    assert (second.job_title_raw, second.employer_name, second.start_date) == ("Caissier", "Magasin Général", "2019-01-01")
    assert result.unmatched_words == ["Service client", "Photoshop", "Arabe", "Anglais"]  # not in this small catalog


DEVELOPER_CV = """SARRA BEN AMOR
Développeuse web
COMPÉTENCES
Technologies: React JS, Redux Toolkit
EXPERIENCE
2024 Stage : Développeuse full-stack NOVATECH
Stage de 6 mois en développement full-stack chez NOVATECH, avec la création d'un site web pour gérer
et présenter les services de l'entreprise.
ÉDUCATION
2021 - 2024 licence en génie logiciel Université: Faculté des Sciences de Monastir
• Développement Web
2020 - 2021 Baccalauréat Lycée Ibn Khaldoun
Baccalauréat en Mathématiques avec mention bien
"""


def test_developer_cv_layout():
    """A common student layout: year before the job, company in capitals, sentences below, school on the line."""
    result = build_draft(DEVELOPER_CV, catalog(("SK-9", "React", ["react js"])))

    [job] = result.draft.experiences  # the sentences below the job describe it, they aren't jobs
    assert (job.job_title_raw, job.employer_name, job.start_date) == (
        "Développeuse full-stack (stage)", "NOVATECH", "2024-01-01",
    )
    assert job.description.startswith("Stage de 6 mois") and job.description.endswith("l'entreprise.")
    assert [(e.level, e.field_of_study, e.institution, e.graduation_year) for e in result.draft.educations] == [
        ("licence", "Génie logiciel", "Faculté des Sciences de Monastir", 2024),
        ("baccalaureate", "Mathématiques", "Lycée Ibn Khaldoun", 2021),  # the second line completes the first
    ]
    assert result.unmatched_words == ["Redux Toolkit"]  # without the "Technologies:" label


def test_pdf_kerning_splits_are_joined():
    assert KERNING_SPLIT.sub(r"\1", "T echnologies: T ailwind, Redux T oolkit, Y a") == (
        "Technologies: Tailwind, Redux Toolkit, Y a"
    )


def test_skills_match_without_accents_or_case():
    draft = build_draft("Ali Ben Ali\nJe parle FRANCAIS et je suis plombier depuis 2015.", CATALOG).draft
    assert {skill.code for skill in draft.skills} == {"SK-3", "SK-5"}


def test_a_year_range_is_not_a_phone_number():
    assert find_phone("Vendeur 2019-2020") == ""
    assert find_phone("Vendeur 2019-2020, tél. 0021698765432") == "+216 98 765 432"


def test_dates_are_removed_from_the_job_line():
    assert find_dates("Serveur, Café du Port (de mars 2018 à juin 2020)") == (
        "2018-03-01", "2020-06-01", "Serveur, Café du Port "
    )


# ---------------------------------------------------------------------------
# POST /me/cv without the database (checks happen before the skills are read)
# ---------------------------------------------------------------------------

@pytest.fixture
def signed_in_no_db(client):
    app.dependency_overrides[get_token_claims] = lambda: {"email": "test@example.tn"}
    app.dependency_overrides[get_db] = lambda: None


def test_cv_rejects_other_file_types(client, signed_in_no_db):
    assert upload(client, "cv.txt", b"Amira Ben Salah, soudeuse", "text/plain").status_code == 415
    assert upload(client, "cv.doc", b"\xd0\xcf\x11\xe0 old Word", "application/msword").status_code == 415
    # The right extension isn't enough: the content must match.
    assert upload(client, "cv.pdf", b"not really a pdf" * 10).status_code == 415
    assert upload(client, "cv.docx", sample("sample_cv.pdf"), DOCX_TYPE).status_code == 415


def test_cv_rejects_files_over_5_mb(client, signed_in_no_db):
    response = upload(client, "cv.pdf", b"%PDF-1.4\n" + b"0" * MAX_CV_BYTES)
    assert response.status_code == 413


def test_cv_without_text_asks_to_fill_the_form(client, signed_in_no_db):
    response = upload(client, "scan.pdf", blank_pdf())
    assert response.status_code == 422
    assert response.json()["detail"] == UNREADABLE == "Nous n'avons pas pu lire ce CV, remplissez le formulaire"


def test_cv_broken_file_gets_the_same_message(client, signed_in_no_db):
    response = upload(client, "cv.docx", b"PK\x03\x04 broken zip", DOCX_TYPE)
    assert response.status_code == 422
    assert response.json()["detail"] == UNREADABLE


def test_cv_needs_login(client, signed_out):
    assert upload(client, "cv.pdf", sample("sample_cv.pdf")).status_code == 401


# ---------------------------------------------------------------------------
# POST /me/cv with the real database (skills come from the catalog)
# ---------------------------------------------------------------------------

@pytest.fixture
def cv_skills(db) -> dict[str, str]:
    """Two catalog skills named in the samples, with test codes; returns {label: code}."""
    tag = uuid.uuid4().hex[:6].upper()
    skills = {"Soudure": f"SK-T{tag}1", "Excel": f"SK-T{tag}2"}
    db.add_all(
        Skill(code=code, label_fr=label, alt_labels=[], skill_type="hard", status="validated")
        for label, code in skills.items()
    )
    db.flush()
    return skills


@pytest.mark.parametrize(
    ("name", "content_type", "full_name", "expected"),
    [
        ("sample_cv.pdf", "application/pdf", "Amira Ben Salah", ["Soudure", "Excel"]),
        ("sample_cv.docx", DOCX_TYPE, "Mohamed Trabelsi", ["Excel"]),
    ],
)
def test_cv_import_returns_a_draft_and_saves_nothing(
    client, signed_in, db, cv_skills, name, content_type, full_name, expected
):
    response = upload(client, name, sample(name), content_type)

    assert response.status_code == 200, response.text
    body = response.json()
    draft = body["draft"]
    assert draft["full_name"] == full_name
    skills = {skill["code"]: skill for skill in draft["skills"]}
    for label in expected:
        assert skills[cv_skills[label]] == {
            "code": cv_skills[label], "label_fr": label, "level": 2, "source": "cv", "confidence": None,
        }
    assert draft["experiences"] and draft["educations"]
    assert isinstance(body["unmatched_words"], list)
    assert db.scalar(select(func.count()).select_from(Candidate).where(Candidate.user_id == signed_in.id)) == 0
