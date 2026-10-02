from pathlib import Path
from uuid import UUID, uuid4

from docx import Document
from fastapi.testclient import TestClient
from mahara_data.schemas.profile import CandidateProfile

from cv_adapter import adapter_profil_vers_contrat
from cv_parser import build_profile_from_cv
from id_utils import canonical_id
from main import app, create_app


DATA_DIR = Path(__file__).parent / "data"


def test_example_cv_adapts_to_wp1_contract():
    brut = build_profile_from_cv(str(DATA_DIR / "cv_exemple.docx"), "cand_demo")
    adapte = adapter_profil_vers_contrat(brut, governorate_code="TN-71")

    profil = CandidateProfile(**adapte)

    assert profil.years_experience == 5
    assert {skill.label_raw for skill in profil.skills} >= {"Python", "Django", "SQL"}


def test_simple_cv_extracts_skills_and_experience(tmp_path):
    cv_path = tmp_path / "cv_simple.docx"
    document = Document()
    document.add_paragraph("Nadia Test")
    document.add_paragraph("Competences techniques")
    document.add_paragraph("Python, SQL")
    document.add_paragraph("Experience professionnelle")
    document.add_paragraph("2 ans d'experience")
    document.save(cv_path)

    profil = build_profile_from_cv(str(cv_path), "cand_simple")

    assert profil["hard_skills"] == ["Python", "SQL"]
    assert profil["experience_annees"] == 2


def test_empty_cv_returns_empty_profile(tmp_path):
    cv_path = tmp_path / "cv_vide.docx"
    Document().save(cv_path)

    profil = build_profile_from_cv(str(cv_path), "cand_vide")

    assert profil["nom"] == "Nom inconnu"
    assert profil["hard_skills"] == []
    assert profil["soft_skills"] == []
    assert profil["experience_annees"] == 0


def test_corrupt_cv_upload_returns_clear_client_error():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/parse-cv",
        params={"candidat_id": str(uuid4())},
        files={"fichier": ("cv_corrompu.docx", b"not a DOCX document")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Le fichier CV est illisible ou corrompu."


def test_profile_persists_across_app_instances_and_legacy_ids_work(tmp_path):
    database_path = tmp_path / "wp3.sqlite3"
    candidate_key = "auto-cand-persist"
    first_app = create_app(database_path)
    with TestClient(first_app) as client:
        parse_response = client.post(
            "/api/v1/parse-cv",
            params={"candidat_id": candidate_key, "governorate_code": "TN-71"},
            files={
                "fichier": (
                    "cv_exemple.docx",
                    (DATA_DIR / "cv_exemple.docx").read_bytes(),
                )
            },
        )
        assert parse_response.status_code == 200
        candidate_uuid = parse_response.json()["profil"]["candidate_id"]
        assert str(UUID(candidate_uuid)) == candidate_uuid

        offers = client.get("/api/v1/offres").json()
        assert all(str(UUID(offer["job_offer_id"])) == offer["job_offer_id"] for offer in offers)

        match_by_legacy_key = client.post(
            "/api/v1/match", params={"candidat_id": candidate_key}
        )
        match_by_uuid = client.post(
            "/api/v1/match", params={"candidat_id": candidate_uuid}
        )
        assert match_by_legacy_key.status_code == 200
        assert match_by_uuid.status_code == 200
        legacy_result = match_by_legacy_key.json()
        uuid_result = match_by_uuid.json()
        assert legacy_result["subject_id"] == candidate_uuid
        assert all(
            str(UUID(item["job_offer_id"])) == item["job_offer_id"]
            for item in legacy_result["items"]
        )
        assert [
            item["job_offer_id"] for item in legacy_result["items"]
        ] == [item["job_offer_id"] for item in uuid_result["items"]]

        backend_offer_uuid = canonical_id("offre-backend")
        roadmap_by_legacy_keys = client.get(
            f"/api/v1/roadmap/{candidate_key}/offre-backend"
        )
        roadmap_by_uuids = client.get(
            f"/api/v1/roadmap/{candidate_uuid}/{backend_offer_uuid}"
        )
        assert roadmap_by_legacy_keys.status_code == 200
        assert roadmap_by_uuids.status_code == 200
        assert roadmap_by_legacy_keys.json() == roadmap_by_uuids.json()

    restarted_app = create_app(database_path)
    with TestClient(restarted_app) as client:
        response = client.post(
            "/api/v1/match", params={"candidat_id": candidate_key}
        )

    assert response.status_code == 200
    assert response.json()["subject_id"] == candidate_uuid
    assert [
        item["job_offer_id"] for item in response.json()["items"]
    ] == [item["job_offer_id"] for item in legacy_result["items"]]
