from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_returns_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "module": "wp5-admin-ministry"}

def test_readiness_reports_every_dependency():
    response = client.get("/api/v1/health/ready")
    assert response.status_code in (200, 503)

    body = response.json()
    assert body["module"] == "wp5-admin-ministry"
    assert {dep["name"] for dep in body["dependencies"]} == {"database", "wp1_schema"}