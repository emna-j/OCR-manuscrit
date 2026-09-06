"""Validation sécurisée des fichiers uploadés (Phase 3, cahier des charges §12).

Vérifie : extension, type MIME réel (octets magiques), taille, contenu
(image lisible / PDF valide), nombre de pages et résolution.
Les erreurs renvoient des messages génériques côté client ; les détails
techniques restent dans les logs sécurisés.
"""
import dataclasses
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()

# Octets magiques par extension (le MIME déclaré par le client n'est pas fiable).
MAGIC_BYTES: dict[str, bytes] = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "pdf": b"%PDF-",
}

CONTENT_TYPE_BY_EXTENSION = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "pdf": "application/pdf",
}

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
PDF_EXTENSION = "pdf"


class UploadValidationError(Exception):
    """Fichier refusé — message générique destiné à l'utilisateur."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclasses.dataclass(frozen=True)
class UploadInfo:
    extension: str
    content_type: str  # normalisé depuis les octets magiques
    page_count: int | None = None
    width: int | None = None
    height: int | None = None


def validate_upload(filename: str, data: bytes) -> UploadInfo:
    """Valide un fichier uploadé et retourne ses informations normalisées."""
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in settings.allowed_extension_list:
        raise UploadValidationError("File type not allowed")

    if not data:
        raise UploadValidationError("Empty file")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise UploadValidationError("File too large")

    # Vérification du contenu réel via les octets magiques.
    expected_magic = MAGIC_BYTES.get(extension)
    if expected_magic is None or not data.startswith(expected_magic):
        logger.warning(f"upload_rejected magic_mismatch extension={extension}")
        raise UploadValidationError("File content does not match its extension")

    if extension in IMAGE_EXTENSIONS:
        return _validate_image(data, extension)
    return _validate_pdf(data)


def _validate_image(data: bytes, extension: str) -> UploadInfo:
    try:
        from PIL import Image

        with Image.open(__import__("io").BytesIO(data)) as image:
            image.verify()  # lève si l'image est corrompue
        with Image.open(__import__("io").BytesIO(data)) as image:
            width, height = image.size
    except Exception:
        logger.warning("upload_rejected invalid_image")
        raise UploadValidationError("Invalid image file")

    if width > settings.max_image_dimension or height > settings.max_image_dimension:
        raise UploadValidationError("Image resolution too large")

    return UploadInfo(
        extension=extension,
        content_type=CONTENT_TYPE_BY_EXTENSION[extension],
        width=width,
        height=height,
    )


def _validate_pdf(data: bytes) -> UploadInfo:
    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=data, filetype="pdf") as document:
            page_count = document.page_count
            if page_count == 0:
                raise UploadValidationError("Invalid PDF file")
            if page_count > settings.max_pdf_pages:
                raise UploadValidationError("PDF has too many pages")
    except UploadValidationError:
        raise
    except Exception:
        logger.warning("upload_rejected invalid_pdf")
        raise UploadValidationError("Invalid PDF file")

    return UploadInfo(extension=PDF_EXTENSION, content_type=CONTENT_TYPE_BY_EXTENSION[PDF_EXTENSION], page_count=page_count)