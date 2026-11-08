from sqlalchemy.exc import OperationalError


def test_liveness_endpoint_reports_process_status(client) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_checks_database(client) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_reports_database_unavailable(client, session, monkeypatch) -> None:
    def fail_query(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))

    monkeypatch.setattr(session, "execute", fail_query)
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Required service unavailable."}
