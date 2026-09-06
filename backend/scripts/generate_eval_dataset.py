"""Génère le dataset d'évaluation (Phase 14).

Dataset SYNTHÉTIQUE : des textes sont rendus avec une police manuscrite
(Ink Free) puis dégradés (inclinaison, bruit, flou, contraste) pour
couvrir les cas du cahier des charges §19 :
lisible, difficile, inclinée, faible qualité, bruit.

Sortie : data/evaluation/samples/*.png + data/evaluation/ground_truth.json

Les résultats produits à partir de ce dataset sont réels mais portent
sur des images générées — à compléter avec de vrais manuscrits.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = PROJECT_ROOT / "data" / "evaluation" / "samples"
GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "evaluation" / "ground_truth.json"

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\Inkfree.ttf",  # police manuscrite
    r"C:\Windows\Fonts\comic.ttf",
]


def _find_font() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return "arial.ttf"  # repli ultime


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.getlength(candidate) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_text(
    text: str,
    font_path: str,
    *,
    width: int = 1000,
    font_size: int = 42,
    tilt: float = 0.0,
    noise: float = 0.0,
    blur: float = 0.0,
    contrast: float = 1.0,
    seed: int = 42,
) -> Image.Image:
    """Rend un texte "manuscrit" synthétique avec les dégradations demandées."""
    random.seed(seed)
    np.random.seed(seed)
    font = ImageFont.truetype(font_path, font_size)
    lines = _wrap(text, font, width - 100)
    line_height = int(font_size * 1.6)
    height = 80 + len(lines) * line_height + 60

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    y = 50
    for line in lines:
        draw.text((60, y), line, font=font, fill=(45, 45, 45))
        y += line_height

    if tilt:
        image = image.rotate(tilt, expand=True, fillcolor="white")
    if noise:
        array = np.asarray(image).astype(float)
        array += np.random.normal(0.0, noise * 255.0, array.shape)
        image = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    if contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    return image


# id -> (texte, sentiment, catégorie, paramètres de rendu)
DATASET: list[dict] = [
    {
        "id": "complaint_retard",
        "text": (
            "Bonjour, je vous écris pour signaler que ma commande est arrivée avec trois "
            "semaines de retard. Le service client n'a jamais répondu à mes appels, "
            "c'est vraiment inacceptable. Je demande un remboursement."
        ),
        "sentiment": "negative",
        "category": "complaint",
        "render": {"tilt": 2.0, "noise": 0.01},
    },
    {
        "id": "complaint_service",
        "text": (
            "Je suis très déçu du service reçu hier. L'agent était impoli et n'a pas résolu "
            "mon problème. Je ne recommande pas cet établissement."
        ),
        "sentiment": "negative",
        "category": "complaint",
        "render": {},
    },
    {
        "id": "compliment_service",
        "text": (
            "Je tenais à vous remercier pour l'excellent accueil reçu lors de ma visite. "
            "Le personnel a été adorable et très professionnel, bravo !"
        ),
        "sentiment": "positive",
        "category": "compliment",
        "render": {"tilt": -1.5},
    },
    {
        "id": "remerciement_rapide",
        "text": "Merci beaucoup pour votre aide, c'était parfait !",
        "sentiment": "positive",
        "category": "thanks",
        "render": {"noise": 0.02, "blur": 0.5},
    },
    {
        "id": "note_rendezvous",
        "text": (
            "Rendez-vous chez le médecin jeudi à dix heures. Ne pas oublier la carte "
            "d'assurance et l'ordonnance."
        ),
        "sentiment": "neutral",
        "category": "note",
        "render": {"tilt": 4.0},
    },
    {
        "id": "demande_info",
        "text": (
            "Bonjour, pourriez-vous m'indiquer les horaires d'ouverture de votre agence "
            "ainsi que le délai de traitement d'un dossier ? Merci."
        ),
        "sentiment": "neutral",
        "category": "request",
        "render": {},
    },
    {
        "id": "reclamation_pii",
        "text": (
            "Je soussigné Ahmed Ben Ali, né le 15/03/1990, conteste la facture numéro "
            "12345678. Vous pouvez me joindre au 22 123 456 ou par courrier."
        ),
        "sentiment": "negative",
        "category": "complaint",
        "render": {"noise": 0.015},
    },
    {
        "id": "ecriture_difficile",
        "text": (
            "Le colis est endommagé et le livreur était pressé. Je souhaite un échange "
            "rapide de la marchandise."
        ),
        "sentiment": "negative",
        "category": "complaint",
        "render": {"tilt": 6.0, "noise": 0.03, "blur": 1.0, "contrast": 0.8},
    },
]


def main() -> None:
    font_path = _find_font()
    print(f"Police : {font_path}")
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    ground_truth = []
    for index, item in enumerate(DATASET):
        image = render_text(item["text"], font_path, seed=1000 + index, **item["render"])
        filename = f"{item['id']}.png"
        image.save(SAMPLES_DIR / filename)
        ground_truth.append(
            {
                "id": item["id"],
                "image": f"samples/{filename}",
                "text": item["text"],
                "sentiment": item["sentiment"],
                "category": item["category"],
            }
        )
        print(f"  généré : {filename} ({image.size[0]}x{image.size[1]})")

    GROUND_TRUTH_PATH.write_text(json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dataset écrit : {len(ground_truth)} documents")
    print(f"Ground truth  : {GROUND_TRUTH_PATH}")


if __name__ == "__main__":
    main()