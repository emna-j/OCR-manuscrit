"""Tests unitaires de la détection PII et de l'anonymisation (Phase 8)."""
from app.models.analysis import PIIType
from app.services.pii_service import anonymize, detect_all, detect_structured


def test_detect_email() -> None:
    spans = detect_structured("Contact: user.name@example.com merci.")
    assert any(s.pii_type == PIIType.EMAIL and s.value == "user.name@example.com" for s in spans)


def test_detect_phone_french() -> None:
    spans = detect_structured("Appelez le 22 123 456 ou le +216 22 123 456.")
    assert any(s.pii_type == PIIType.PHONE for s in spans)


def test_detect_date_of_birth() -> None:
    spans = detect_structured("Né le 15/03/1990 à Tunis.")
    assert any(s.pii_type == PIIType.DATE_OF_BIRTH for s in spans)


def test_detect_id_number() -> None:
    spans = detect_structured("CIN numéro 12345678.")
    assert any(s.pii_type == PIIType.ID_NUMBER and s.value == "12345678" for s in spans)


def test_anonymize_example() -> None:
    """Exemple du cahier des charges §11."""
    text = "Ahmed Ben Ali peut être contacté au 22123456."
    # "Ahmed Ben Ali" via Gemini (mocké), "22123456" via regex phone.
    spans = detect_all(text, use_gemini=False)
    # Le numéro est détecté par la regex téléphone.
    anonymized = anonymize(text, spans)
    assert "[PHONE]" in anonymized


def test_anonymize_merges_gemini_entities(mock_gemini) -> None:
    text = "Ahmed Ben Ali peut être contacté au 22123456."
    mock_gemini(entities=[{"type": "PERSON", "value": "Ahmed Ben Ali", "start": 0, "end": 14, "confidence": 0.9}])
    spans = detect_all(text, use_gemini=True)
    anonymized = anonymize(text, spans)
    assert "[PERSON]" in anonymized
    assert "Ahmed Ben Ali" not in anonymized


def test_no_pii_plain_text() -> None:
    spans = detect_structured("Ceci est un texte simple sans information personnelle.")
    assert spans == []