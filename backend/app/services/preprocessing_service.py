"""Prétraitement des documents (Phase 4) — amélioration de la reconnaissance.

Pour chaque page (image unique ou pages d'un PDF) :
1. conversion en niveaux de gris ;
2. débruitage (Non-Local Means) ;
3. redressement (deskew) ;
4. amélioration du contraste (CLAHE).

La sortie est une liste d'images PNG prêtes pour Gemini.
Le seuillage binaire est volontairement évité : les VLM lisent mieux les
niveaux de gris originaux que les binaires agressifs (choix documenté).
"""
import io

import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()

_PNG_MIME = "image/png"


def _preprocess_gray(gray: np.ndarray) -> np.ndarray:
    """Applique le pipeline OpenCV sur une image en niveaux de gris."""
    # Débruitage conservateur (h=10) : réduit le bruit sans effacer l'encre.
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    # Redressement.
    deskewed = _deskew(denoised)
    # Contraste local.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(deskewed)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Estime et corrige l'inclinaison de la page."""
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) < 100:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.5:
        return gray
    height, width = gray.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _to_png_bytes(gray: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", gray)
    if not ok:
        raise ValueError("Failed to encode preprocessed image")
    return buffer.tobytes()


def preprocess_image_bytes(image_bytes: bytes) -> bytes:
    """Prétraite une image et retourne un PNG (bytes)."""
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unreadable image")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return _to_png_bytes(_preprocess_gray(gray))


def _pdf_to_png_pages(pdf_bytes: bytes) -> list[bytes]:
    import fitz  # PyMuPDF

    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        pages: list[bytes] = []
        for page in document:
            if len(pages) >= settings.max_pdf_pages:
                break
            pixmap = page.get_pixmap(dpi=200)
            pages.append(pixmap.tobytes("png"))
        return pages


def prepare_document_pages(data: bytes, content_type: str) -> list[bytes]:
    """Retourne les pages du document en PNG prétraité.

    - image : une seule page ;
    - PDF : chaque page rendue en image puis prétraitée.
    """
    if content_type == "application/pdf":
        raw_pages = _pdf_to_png_pages(data)
        return [_to_png_bytes(_preprocess_gray(cv2.cvtColor(cv2.imdecode(np.frombuffer(p, np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2GRAY))) for p in raw_pages]
    return [preprocess_image_bytes(data)]