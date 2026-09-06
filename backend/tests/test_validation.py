"""Tests unitaires de la validation des fichiers (Phase 3)."""
import pytest

from app.services.validation_service import UploadValidationError, validate_upload
from tests.helpers import make_jpg_bytes, make_pdf_bytes, make_png_bytes


def test_valid_png() -> None:
    info = validate_upload("note.png", make_png_bytes())
    assert info.content_type == "image/png"
    assert info.width == 100
    assert info.height == 100


def test_valid_jpg() -> None:
    info = validate_upload("photo.jpg", make_jpg_bytes())
    assert info.content_type == "image/jpeg"


def test_valid_pdf() -> None:
    info = validate_upload("doc.pdf", make_pdf_bytes())
    assert info.content_type == "application/pdf"
    assert info.page_count == 1


def test_reject_disallowed_extension() -> None:
    with pytest.raises(UploadValidationError, match="File type not allowed"):
        validate_upload("malware.exe", b"MZ....")


def test_reject_empty_file() -> None:
    with pytest.raises(UploadValidationError, match="Empty file"):
        validate_upload("empty.png", b"")


def test_reject_oversized_file(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    with pytest.raises(UploadValidationError, match="File too large"):
        validate_upload("big.png", make_png_bytes())


def test_reject_forged_extension() -> None:
    # Un PDF déguisé en PNG.
    with pytest.raises(UploadValidationError, match="does not match its extension"):
        validate_upload("fake.png", make_pdf_bytes())


def test_reject_corrupted_image() -> None:
    with pytest.raises(UploadValidationError, match="Invalid image"):
        validate_upload("broken.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


def test_reject_pdf_too_many_pages(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_pdf_pages", 0)
    with pytest.raises(UploadValidationError, match="too many pages"):
        validate_upload("many.pdf", make_pdf_bytes())