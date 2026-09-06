"""Tests API des statistiques du dashboard."""
from fastapi.testclient import TestClient

from app.models.user import UserRole
from tests.helpers import make_png_bytes


def test_dashboard_empty(client: TestClient, make_user) -> None:
    _, headers = make_user()
    response = client.get("/api/dashboard/statistics", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_documents"] == 0
    assert body["requires_review_count"] == 0


def test_dashboard_counts_and_averages(client: TestClient, make_user, mock_gemini) -> None:
    _, analyst_headers = make_user(UserRole.ANALYST)

    # Document positif haute confiance.
    mock_gemini(ocr_confidence=0.95, sentiment="positive", sentiment_confidence=0.9)
    first = client.post(
        "/api/documents/upload", headers=analyst_headers,
        files={"file": ("a.png", make_png_bytes(), "image/png")},
    ).json()["id"]
    client.post(f"/api/documents/{first}/analyze", headers=analyst_headers)

    # Document négatif basse confiance -> REQUIRES_REVIEW.
    mock_gemini(ocr_confidence=0.60, sentiment="negative", sentiment_confidence=0.5)
    second = client.post(
        "/api/documents/upload", headers=analyst_headers,
        files={"file": ("b.png", make_png_bytes(), "image/png")},
    ).json()["id"]
    client.post(f"/api/documents/{second}/analyze", headers=analyst_headers)

    body = client.get("/api/dashboard/statistics", headers=analyst_headers).json()
    assert body["total_documents"] == 2
    assert body["positive_count"] == 1
    assert body["negative_count"] == 1
    assert body["requires_review_count"] == 1
    assert body["average_ocr_confidence"] is not None
    assert len(body["recent_documents"]) == 2


def test_dashboard_scoped_per_user(client: TestClient, make_user, mock_gemini) -> None:
    mock_gemini()
    _, analyst_headers = make_user(UserRole.ANALYST)
    _, user_headers = make_user(UserRole.USER)

    doc = client.post(
        "/api/documents/upload", headers=analyst_headers,
        files={"file": ("a.png", make_png_bytes(), "image/png")},
    ).json()["id"]
    client.post(f"/api/documents/{doc}/analyze", headers=analyst_headers)

    assert client.get("/api/dashboard/statistics", headers=user_headers).json()["total_documents"] == 0
    assert client.get("/api/dashboard/statistics", headers=analyst_headers).json()["total_documents"] == 1