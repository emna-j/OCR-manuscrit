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


def test_analyze_twice_reuses_analysis(client: TestClient, make_user, mock_gemini) -> None:
    """Régression : deux analyses successives ne doivent pas violer la contrainte unique."""
    mock_gemini(ocr_confidence=0.95, sentiment="positive", sentiment_confidence=0.9)
    _, headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, headers)

    first = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert first.status_code == 200
    second = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert second.status_code == 200
    # Même analyse réutilisée (pas de doublon).
    assert second.json()["id"] == first.json()["id"]


def test_analyze_after_failure_rerun(client: TestClient, make_user, mock_gemini, monkeypatch) -> None:
    """Régression : un run échoué puis relancé ne crée pas de doublon (500)."""
    from app.services import gemini_service

    mock_gemini()
    _, headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, headers)

    def boom(*args, **kwargs):
        raise gemini_service.GeminiError("boom")

    monkeypatch.setattr(gemini_service, "extract_manuscript", boom)
    assert client.post(f"/api/documents/{doc_id}/analyze", headers=headers).status_code == 502

    # Relance après échec : doit réussir sans erreur d'intégrité.
    mock_gemini(ocr_confidence=0.9, sentiment="neutral", sentiment_confidence=0.8)
    response = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert response.status_code == 200
    assert response.json()["sentiment"] == "neutral"


def test_analyze_failed_rerun_preserves_previous_analysis(client: TestClient, make_user, mock_gemini, monkeypatch) -> None:
    """Régression : une ré-analyse forcée qui échoue ne détruit pas la dernière bonne analyse."""
    from app.services import gemini_service

    mock_gemini(ocr_confidence=0.95, sentiment="positive", sentiment_confidence=0.9, category="education")
    _, headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, headers)

    first = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert first.status_code == 200
    assert first.json()["category"] == "education"

    def boom(*args, **kwargs):
        raise gemini_service.GeminiError("boom")

    monkeypatch.setattr(gemini_service, "extract_manuscript", boom)
    # Requête forcée : le document est COMPLETED, sans force le cache court-circuiterait.
    assert client.post(f"/api/documents/{doc_id}/analyze?force=1", headers=headers).status_code == 502

    detail = client.get(f"/api/documents/{doc_id}", headers=headers).json()
    assert detail["status"] == "FAILED"
    # L'analyse précédente est conservée (pas de rupture de données sur échec transitoire).
    assert detail["analysis"]["category"] == "education"
    assert detail["analysis"]["extracted_text"] is not None


def test_analyze_quota_exceeded_explicit_message(client: TestClient, make_user, monkeypatch) -> None:
    """Régression : un 429 RESOURCE_EXHAUSTED donne un 502 explicite, pas un message générique."""
    from app.services import gemini_service

    _, headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, headers)

    quota_error = Exception(
        "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
        "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, "
        "model: gemini-3.6-flash"
    )
    gemini_error = gemini_service.GeminiError("Gemini extraction call failed")
    gemini_error.__cause__ = quota_error

    def boom(*args, **kwargs):
        raise gemini_error

    monkeypatch.setattr(gemini_service, "extract_manuscript", boom)
    response = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert response.status_code == 502
    assert response.json()["detail"] == "Analysis failed: Gemini quota exceeded, please retry later"


def test_analyze_cached_without_force(client: TestClient, make_user, mock_gemini, monkeypatch) -> None:
    """Régression : ré-analyse d'un document terminé sans `force` -> cache instantané (zéro appel Gemini)."""
    from app.services import gemini_service

    calls = {"count": 0}

    def counting_extract(images, mime_type="image/png"):
        calls["count"] += 1
        return gemini_service.ExtractionResult(
            language="fr",
            text="Texte de test.",
            lines=[{"text": "Texte de test.", "confidence": 0.95}],
            overall_confidence=0.95,
            uncertain_segments=[],
        )

    mock_gemini(ocr_confidence=0.95, sentiment="positive", sentiment_confidence=0.9)
    monkeypatch.setattr(gemini_service, "extract_manuscript", counting_extract)

    _, headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, headers)

    first = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert first.status_code == 200
    assert calls["count"] == 1

    # Reclique sans force : l'analyse existante est réutilisée, aucun appel Gemini.
    second = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert calls["count"] == 1

    # Force : le pipeline est relancé (un nouvel appel Gemini).
    forced = client.post(f"/api/documents/{doc_id}/analyze?force=1", headers=headers)
    assert forced.status_code == 200
    assert calls["count"] == 2


def test_get_analysis_not_found(client: TestClient, make_user) -> None:
    _, headers = make_user(UserRole.ANALYST)
    doc_id = _upload(client, headers)
    assert client.get(f"/api/documents/{doc_id}/analysis", headers=headers).status_code == 404