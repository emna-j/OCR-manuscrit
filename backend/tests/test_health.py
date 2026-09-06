"""Tests de l'endpoint de santé."""
from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert "version" in body


def test_openapi_disponible(client: TestClient) -> None:
    """Swagger/OpenAPI doit être exposé (cahier des charges §22)."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]