"""Tests API de la revue humaine (Human-in-the-loop)."""
from fastapi.testclient import TestClient

from app.models.user import UserRole
from tests.helpers import make_png_bytes


def _analyzed_document(client: TestClient, mock_gemini, make_user, role: UserRole = UserRole.ANALYST) -> tuple[str, dict]:
    mock_gemini(ocr_confidence=0.60, sentiment="negative", sentiment_confidence=0.55)
    _, analyst_headers = make_user(role)
    upload = client.post(
        "/api/documents/upload",
        headers=analyst_headers,
        files={"file": ("note.png", make_png_bytes(), "image/png")},
    )
    doc_id = upload.json()["id"]
    client.post(f"/api/documents/{doc_id}/analyze", headers=analyst_headers)
    return doc_id, analyst_headers


def test_review_requires_reviewer_role(client: TestClient, make_user, mock_gemini) -> None:
    doc_id, analyst_headers = _analyzed_document(client, mock_gemini, make_user)
    _, user_headers = make_user(UserRole.USER)
    response = client.post(
        f"/api/documents/{doc_id}/review",
        headers=user_headers,
        json={"decision": "VALIDATED"},
    )
    assert response.status_code == 403


def test_review_validate_with_corrections(client: TestClient, make_user, mock_gemini) -> None:
    doc_id, analyst_headers = _analyzed_document(client, mock_gemini, make_user)
    _, reviewer_headers = make_user(UserRole.REVIEWER)

    response = client.post(
        f"/api/documents/{doc_id}/review",
        headers=reviewer_headers,
        json={
            "corrected_text": "Texte corrigé par le reviewer.",
            "corrected_sentiment": "positive",
            "corrected_category": "compliment",
            "comment": "Transcription corrigée",
            "decision": "VALIDATED",
        },
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "VALIDATED"

    detail = client.get(f"/api/documents/{doc_id}", headers=analyst_headers).json()
    assert detail["status"] == "REVIEWED"
    assert detail["analysis"]["extracted_text"] == "Texte corrigé par le reviewer."
    assert detail["analysis"]["sentiment"] == "positive"
    assert detail["latest_review"]["comment"] == "Transcription corrigée"


def test_review_reject_marks_failed(client: TestClient, make_user, mock_gemini) -> None:
    doc_id, analyst_headers = _analyzed_document(client, mock_gemini, make_user)
    _, reviewer_headers = make_user(UserRole.REVIEWER)

    response = client.post(
        f"/api/documents/{doc_id}/review",
        headers=reviewer_headers,
        json={"comment": "Document illisible", "decision": "REJECTED"},
    )
    assert response.status_code == 200

    detail = client.get(f"/api/documents/{doc_id}", headers=analyst_headers).json()
    assert detail["status"] == "FAILED"
    assert detail["error_reason"] == "Rejected by reviewer"


def test_review_unreviewable_status(client: TestClient, make_user, mock_gemini) -> None:
    mock_gemini()
    _, analyst_headers = make_user(UserRole.ANALYST)
    upload = client.post(
        "/api/documents/upload",
        headers=analyst_headers,
        files={"file": ("note.png", make_png_bytes(), "image/png")},
    )
    doc_id = upload.json()["id"]  # statut UPLOADED : pas revue possible
    _, reviewer_headers = make_user(UserRole.REVIEWER)
    response = client.post(
        f"/api/documents/{doc_id}/review",
        headers=reviewer_headers,
        json={"decision": "VALIDATED"},
    )
    assert response.status_code == 409