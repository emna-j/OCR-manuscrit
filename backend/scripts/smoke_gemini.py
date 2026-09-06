"""Vérification de l'intégration Gemini réelle (clé depuis .env).

Génère une image synthétique (texte rendu par PIL), la prétraite,
l'envoie à Gemini pour extraction, puis analyse le texte extrait.

Usage (depuis backend/) :
    .venv/Scripts/python scripts/smoke_gemini.py
"""
import io
import sys
import time
from pathlib import Path

# Permet d'exécuter ce script directement : .venv/Scripts/python scripts/smoke_gemini.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont

from app.services import gemini_service, preprocessing_service

SAMPLE_TEXTS = [
    "Bonjour, ceci est un document de test manuscrit.",
    "Je suis très satisfait du service, merci beaucoup !",
]


def _render_text_image(text: str, font_path: str = r"C:\Windows\Fonts\arial.ttf") -> bytes:
    """Rend un texte sur une image blanche (synthétique, pour tests)."""
    font = ImageFont.truetype(font_path, 40)
    width = 40 + font.getbbox(text)[2] + 40
    height = 140
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 50), text, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    print(f"Modèle : {__import__('app.core.config', fromlist=['settings']).settings.gemini_model}")
    print(f"Clé configurée : {'oui' if __import__('app.core.config', fromlist=['settings']).settings.gemini_api_key else 'NON !'}")

    for text in SAMPLE_TEXTS:
        print("\n" + "=" * 60)
        print(f"Texte source : {text!r}")

        raw = _render_text_image(text)
        pages = preprocessing_service.prepare_document_pages(raw, "image/png")

        start = time.perf_counter()
        extraction = gemini_service.extract_manuscript(pages)
        duration = time.perf_counter() - start
        print(f"Extraction ({duration:.1f}s) :")
        print(f"  texte         : {extraction.text!r}")
        print(f"  langue        : {extraction.language}")
        print(f"  confiance OCR : {extraction.overall_confidence:.2f}")
        print(f"  lignes        : {len(extraction.lines)}")

        start = time.perf_counter()
        analysis = gemini_service.analyze_text(extraction.text)
        duration = time.perf_counter() - start
        print(f"Analyse ({duration:.1f}s) :")
        print(f"  sentiment : {analysis.sentiment} ({analysis.sentiment_confidence:.2f})")
        print(f"  émotions  : {analysis.emotions}")
        print(f"  catégorie : {analysis.category}")
        print(f"  mots-clés : {analysis.keywords}")
        print(f"  résumé    : {analysis.summary!r}")


if __name__ == "__main__":
    main()