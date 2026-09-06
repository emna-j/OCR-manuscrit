"""Helpers de test."""
import io

from PIL import Image


def make_png_bytes(color: tuple[int, int, int] = (255, 255, 255), size: tuple[int, int] = (100, 100)) -> bytes:
    """Génère une petite image PNG valide en mémoire."""
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_jpg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100), (200, 200, 200)).save(buffer, format="JPEG")
    return buffer.getvalue()


def make_pdf_bytes() -> bytes:
    """Génère un petit PDF 1 page via PyMuPDF."""
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Manuscript test document")
    return document.tobytes()