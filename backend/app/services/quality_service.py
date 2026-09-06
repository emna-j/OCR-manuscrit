"""Contrôle qualité et scoring de confiance (Phase 9, cahier des charges §14).

Règles (seuils configurables, valeurs provisoires à calibrer en Phase 14) :
- confiance OCR < seuil OCR  → REQUIRES_REVIEW ;
- confiance analyse < seuil  → REQUIRES_REVIEW ;
- sinon                      → COMPLETED.

Les seuils ne sont PAS présentés comme des valeurs scientifiquement
validées : ils sont calibrés sur le dataset d'évaluation.
"""
import dataclasses

from app.core.config import settings
from app.core.logging import get_logger
from app.models.analysis import Sentiment

logger = get_logger()

VALID_SENTIMENTS = {s.value for s in Sentiment}


@dataclasses.dataclass(frozen=True)
class QualityDecision:
    requires_review: bool
    ocr_confidence: float
    analysis_confidence: float
    reasons: list[str]


def evaluate(
    ocr_confidence: float,
    analysis_confidence: float,
    sentiment: str | None,
) -> QualityDecision:
    """Évalue la qualité du résultat et décide si une revue humaine est requise."""
    reasons: list[str] = []

    if ocr_confidence < settings.ocr_confidence_threshold:
        reasons.append(f"OCR confidence {ocr_confidence:.2f} below threshold {settings.ocr_confidence_threshold:.2f}")

    if analysis_confidence < settings.analysis_confidence_threshold:
        reasons.append(
            f"Analysis confidence {analysis_confidence:.2f} below threshold {settings.analysis_confidence_threshold:.2f}"
        )

    if sentiment is not None and sentiment not in VALID_SENTIMENTS:
        reasons.append(f"Invalid sentiment value: {sentiment!r}")

    requires_review = len(reasons) > 0
    if requires_review:
        logger.info(f"quality_requires_review reasons={reasons}")
    return QualityDecision(
        requires_review=requires_review,
        ocr_confidence=ocr_confidence,
        analysis_confidence=analysis_confidence,
        reasons=reasons,
    )