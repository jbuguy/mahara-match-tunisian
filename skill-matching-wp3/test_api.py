from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document
from fastapi.testclient import TestClient

import main
from main import create_app
from mahara_data.schemas.matching import Roadmap


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "wp3.sqlite3")) as test_client:
        yield test_client


def upload_cv(client, candidate_id, content=None):
    if content is None:
        content = (Path(__file__).parent / "data" / "cv_exemple.docx").read_bytes()
    return client.post(
        "/api/v1/parse-cv",
        params={"candidat_id": candidate_id, "governorate_code": "TN-71"},
        files={"fichier": ("candidate.docx", content)},
    )


def simple_cv_bytes(*lines):
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_get_and_post_roadmap_return_same_wp1_valid_result(client):
    candidate_id = "roadmap-gap-candidate"
    assert upload_cv(client, candidate_id).status_code == 200

    get_response = client.get(
        f"/api/v1/roadmap/{candidate_id}/offre-backend"
    )
    post_response = client.post(
        "/api/v1/roadmap",
        json={"candidate_id": candidate_id, "job_offer_id": "offre-backend"},
    )

    assert get_response.status_code == 200
    assert post_response.status_code == 200
    assert get_response.json() == post_response.json()
    Roadmap(**post_response.json())


def test_get_and_post_roadmap_report_no_gap(client):
    candidate_id = "roadmap-no-gap-candidate"
    cv = simple_cv_bytes(
        "Nadia Test",
        "Competences techniques",
        "Irrigation",
        "Experience professionnelle",
        "2 ans d'experience",
    )
    assert upload_cv(client, candidate_id, cv).status_code == 200

    get_response = client.get(
        f"/api/v1/roadmap/{candidate_id}/offre-agricole"
    )
    post_response = client.post(
        "/api/v1/roadmap",
        json={"candidate_id": candidate_id, "job_offer_id": "offre-agricole"},
    )

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "no_gap"
    assert post_response.status_code == 200
    assert post_response.json() == get_response.json()


def test_unknown_profile_returns_404(client):
    response = client.post(
        "/api/v1/match", params={"candidat_id": f"missing-{uuid4()}"}
    )

    assert response.status_code == 404


def test_unknown_offer_returns_404_for_get_and_post(client):
    candidate_id = "known-roadmap-candidate"
    assert upload_cv(client, candidate_id).status_code == 200

    get_response = client.get(
        f"/api/v1/roadmap/{candidate_id}/unknown-offer"
    )
    post_response = client.post(
        "/api/v1/roadmap",
        json={"candidate_id": candidate_id, "job_offer_id": "unknown-offer"},
    )

    assert get_response.status_code == 404
    assert post_response.status_code == 404


def test_skills_endpoint_maps_codes_and_normalizes_unmapped_labels(client):
    response = client.get("/api/v1/skills")
    unmapped_response = client.get(
        "/api/v1/skills", params={"skill_code": "UNMAPPED:  Irrigation  "}
    )

    assert response.status_code == 200
    labels = response.json()
    assert labels["SK-0101"] == "Python"
    assert labels["SK-9017"] == "Kubernetes"
    assert unmapped_response.status_code == 200
    assert unmapped_response.json() == {"UNMAPPED:  Irrigation  ": "irrigation"}


@pytest.mark.parametrize(
    ("port_value", "expected_port"),
    [("8001", 8001), (None, 8000)],
)
def test_server_port_uses_port_environment_variable(
    monkeypatch, port_value, expected_port
):
    calls = []
    if port_value is None:
        monkeypatch.delenv("PORT", raising=False)
    else:
        monkeypatch.setenv("PORT", port_value)
    monkeypatch.setattr(main.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))

    main.run()

    assert calls[0]["port"] == expected_port
