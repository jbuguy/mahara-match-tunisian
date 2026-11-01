from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_cors_asgi_app


def test_cors_headers_are_added_to_unhandled_error_responses():
    app = FastAPI()

    @app.get("/failure")
    def fail():
        raise RuntimeError("test failure")

    client = TestClient(create_cors_asgi_app(app), raise_server_exceptions=False)
    response = client.get(
        "/failure",
        headers={"Origin": "http://127.0.0.1:5174"},
    )

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
