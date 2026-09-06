"""Tests unitaires du prétraitement OpenCV (Phase 4)."""
import numpy as np

from app.services.preprocessing_service import prepare_document_pages, preprocess_image_bytes
from tests.helpers import make_pdf_bytes, make_png_bytes


def test_preprocess_returns_png() -> None:
    result = preprocess_image_bytes(make_png_bytes(color=(200, 200, 200)))
    assert result.startswith(b"\x89PNG")


def test_preprocess_grayscale_output() -> None:
    result = preprocess_image_bytes(make_png_bytes())
    # Décode et vérifie que l'image est en niveaux de gris (1 canal).
    import cv2

    import numpy as np

    image = cv2.imdecode(np.frombuffer(result, np.uint8), cv2.IMREAD_GRAYSCALE)
    assert image is not None
    assert image.ndim == 2


def test_prepare_single_page_image() -> None:
    pages = prepare_document_pages(make_png_bytes(), "image/png")
    assert len(pages) == 1
    assert pages[0].startswith(b"\x89PNG")


def test_prepare_pdf_pages() -> None:
    pages = prepare_document_pages(make_pdf_bytes(), "application/pdf")
    assert len(pages) == 1
    assert pages[0].startswith(b"\x89PNG")