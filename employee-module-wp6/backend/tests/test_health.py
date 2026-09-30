from app.db import get_db
from app.main import app


class FakeSession:
    def __init__(self, result=None, error: Exception | None = None):
        self.result, self.error = result, error

    def scalar(self, _statement):
        if self.error:
            raise self.error
        return self.result


def test_health_returns_governorate_count(client):
    app.dependency_overrides[get_db] = lambda: FakeSession(result=24)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "governorates": 24}


def test_health_reports_database_error(client):
    app.dependency_overrides[get_db] = lambda: FakeSession(error=RuntimeError("down"))
    response = client.get("/api/v1/health")
    assert response.status_code == 503
