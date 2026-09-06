"""Détection PII et anonymisation (Phase 8, cahier des charges §11).

Stratégie hybride :
1. détecteurs déterministes (regex) pour les types structurés :
   EMAIL, PHONE, DATE_OF_BIRTH, ID_NUMBER ;
2. complément Gemini (NER) pour PERSON, ADDRESS, ORGANIZATION, LOCATION ;
3. fusion par position (les regex font foi pour leurs types) ;
4. anonymisation : remplacement des segments détectés par `[TYPE]`.

Les valeurs détectées sont conservées en base pour la revue humaine mais
ne sont jamais envoyées aux logs ni au frontend sans autorisation.
"""
import re
from dataclasses import dataclass

from app.core.logging import get_logger
from app.models.analysis import PIIType
from app.services import gemini_service

logger = get_logger()

# (type, regex) — ordre important : les plus spécifiques d'abord.
# ID_NUMBER est contextuel (mot-clé CIN/n°/numéro/ID) pour ne pas entrer
# en collision avec les numéros de téléphone.
_STRUCTURED_DETECTORS: list[tuple[PIIType, re.Pattern[str]]] = [
    (PIIType.EMAIL, re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    (PIIType.DATE_OF_BIRTH, re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
    (PIIType.ID_NUMBER, re.compile(r"(?i)\b(?:cin|n°|nº|no\.?|numéro|numero|id)\b[\s:.\(\)-]*(\d{6,12})")),
    (PIIType.PHONE, re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}(?!\d)")),
]

# Pour ID_NUMBER, seule la partie chiffres (groupe 1) est retenue :
# on anonymise le numéro, pas le mot-clé qui le précède.
_USE_GROUP_1 = {PIIType.ID_NUMBER}


@dataclass(frozen=True)
class PIISpan:
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float


def detect_structured(text: str) -> list[PIISpan]:
    """Détection regex des PII structurées."""
    spans: list[PIISpan] = []
    for pii_type, pattern in _STRUCTURED_DETECTORS:
        for match in pattern.finditer(text):
            if pii_type in _USE_GROUP_1:
                value = match.group(1)
                start, end = match.start(1), match.end(1)
            else:
                value = match.group(0)
                start, end = match.start(), match.end()
            spans.append(PIISpan(pii_type=pii_type, value=value, start=start, end=end, confidence=0.95))
    return _merge_overlaps(spans)


def detect_all(text: str, use_gemini: bool = True) -> list[PIISpan]:
    """Détection complète : regex + NER Gemini (si disponible), fusionnée."""
    spans = detect_structured(text)
    detected_types = {span.pii_type for span in spans}

    if use_gemini:
        try:
            entities = gemini_service.detect_entities(text)
        except gemini_service.GeminiError:
            entities = []
        for entity in entities:
            try:
                pii_type = PIIType(entity.get("type", "").upper())
            except ValueError:
                continue
            if pii_type in detected_types:
                continue  # les regex font foi pour les types structurés
            value = str(entity.get("value", "")).strip()
            if not value:
                continue
            start = entity.get("start")
            end = entity.get("end")
            if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
                actual = text[start:end]
                if actual and actual in text:
                    spans.append(PIISpan(pii_type=pii_type, value=actual, start=start, end=end, confidence=0.7))
                    continue
            # Repli : recherche textuelle de la valeur.
            index = text.find(value)
            if index != -1:
                spans.append(
                    PIISpan(pii_type=pii_type, value=value, start=index, end=index + len(value), confidence=0.7)
                )
    return _merge_overlaps(spans)


def _merge_overlaps(spans: list[PIISpan]) -> list[PIISpan]:
    """Supprime les chevauchements : garde le segment le plus long."""
    spans.sort(key=lambda s: (s.start, -(s.end - s.start)))
    merged: list[PIISpan] = []
    for span in spans:
        if merged and span.start < merged[-1].end:
            prev = merged[-1]
            if (span.end - span.start) > (prev.end - prev.start):
                merged[-1] = span
            continue
        merged.append(span)
    return merged


def anonymize(text: str, spans: list[PIISpan]) -> str:
    """Remplace les PII détectées par `[TYPE]`.

    Exemple : "Ahmed Ben Ali peut être contacté au 22123456."
    -> "[PERSON] peut être contacté au [PHONE]."
    """
    if not spans:
        return text
    ordered = sorted(spans, key=lambda s: s.start)
    parts: list[str] = []
    cursor = 0
    for span in ordered:
        if span.start < cursor:
            continue
        parts.append(text[cursor : span.start])
        parts.append(f"[{span.pii_type.value}]")
        cursor = span.end
    parts.append(text[cursor:])
    return "".join(parts)