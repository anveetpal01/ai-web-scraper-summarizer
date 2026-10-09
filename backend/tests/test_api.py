import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("body", [{}, {"link": "https://example.com"}, {"url": 123}])
def test_rejects_bad_request_body(body: dict) -> None:
    response = client.post("/api/summarize", json=body)
    assert response.status_code == 400
    assert "error" in response.json()


def test_rejects_unsupported_scheme() -> None:
    response = client.post("/api/summarize", json={"url": "ftp://example.com"})
    assert response.status_code == 400
    assert response.json() == {"error": "Only http:// and https:// URLs are supported."}


def test_reports_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.summarizer.get_settings", lambda: Settings("", "gemini-test", []))
    response = client.post("/api/summarize", json={"url": "https://example.com"})
    assert response.status_code == 500
    assert "GEMINI_API_KEY" in response.json()["error"]


def test_cors_allows_local_frontend() -> None:
    response = client.options(
        "/api/summarize",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
