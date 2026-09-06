"""Tests API du pipeline d'analyse (avec Gemini mocké, offline)."""
from fastapi.testclient import TestClient

from app.models.document import DocumentStatus
from app.models.user import UserRole
from tests.helpers import make_png_bytes


def _upload(client: TestClient, headers: dict) -> str:
    response = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("note.png", make_png_bytes(), "image/png")},
    )
    return response.json()["id"]


def test_analyze_requires_analyst_role(client: TestClient, make_user) -> None:
    user, headers = make_user(UserRole.USER)
    doc_id = _upload(client, headers)
    response = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert response.status_code == 403


def test_analyze_full_pipeline_high_confidence(client: TestClient, make_user, mock_gemini) -> None:
    mock_gemini(ocr_confidence=0.95, sentiment="positive", sentiment_confidence=0.9)
    _, analyst_headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, analyst_headers)

    response = client.post(f"/api/documents/{doc_id}/analyze", headers=analyst_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["extracted_text"] == "Bonjour, ceci est un document de test."
    assert body["sentiment"] == "positive"
    assert body["ocr_confidence"] == 0.95
    assert body["pii_detections"] == []

    # Le document passe en COMPLETED (confiances élevées).
    detail = client.get(f"/api/documents/{doc_id}", headers=analyst_headers).json()
    assert detail["status"] == "COMPLETED"
    assert detail["analysis"]["category"] == "note"


def test_analyze_low_ocr_confidence_requires_review(client: TestClient, make_user, mock_gemini) -> None:
    mock_gemini(ocr_confidence=0.60, sentiment_confidence=0.9)
    _, analyst_headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, analyst_headers)

    client.post(f"/api/documents/{doc_id}/analyze", headers=analyst_headers)
    detail = client.get(f"/api/documents/{doc_id}", headers=analyst_headers).json()
    assert detail["status"] == "REQUIRES_REVIEW"


def test_analyze_low_analysis_confidence_requires_review(client: TestClient, make_user, mock_gemini) -> None:
    mock_gemini(ocr_confidence=0.95, sentiment_confidence=0.40)
    _, analyst_headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, analyst_headers)

    client.post(f"/api/documents/{doc_id}/analyze", headers=analyst_headers)
    detail = client.get(f"/api/documents/{doc_id}", headers=analyst_headers).json()
    assert detail["status"] == "REQUIRES_REVIEW"


def test_analyze_detects_pii_and_anonymizes(client: TestClient, make_user, mock_gemini) -> None:
    mock_gemini(extraction_text="Contactez Ahmed au 22123456 ou par mail user@test.com", ocr_confidence=0.9)
    _, analyst_headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, analyst_headers)

    response = client.post(f"/api/documents/{doc_id}/analyze", headers=analyst_headers)
    assert response.status_code == 200
    pii_types = {p["pii_type"] for p in response.json()["pii_detections"]}
    assert "PHONE" in pii_types
    assert "EMAIL" in pii_types


def test_analyze_failure_marks_failed(client: TestClient, make_user, mock_gemini, monkeypatch) -> None:
    from app.services import gemini_service

    mock_gemini()
    _, analyst_headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, analyst_headers)

    def boom(*args, **kwargs):
        raise gemini_service.GeminiError("boom")

    monkeypatch.setattr(gemini_service, "extract_manuscript", boom)
    response = client.post(f"/api/documents/{doc_id}/analyze", headers=analyst_headers)
    assert response.status_code == 502
    assert response.json()["detail"] == "Analysis failed"

    detail = client.get(f"/api/documents/{doc_id}", headers=analyst_headers).json()
    assert detail["status"] == "FAILED"


def test_get_analysis_not_found(client: TestClient, make_user) -> None:
    _, headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, headers)
    assert client.get(f"/api/documents/{doc_id}/analysis", headers=headers).status_code == 404