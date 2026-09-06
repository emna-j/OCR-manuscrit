"""Métriques d'évaluation IA (Phase 14, cahier des charges §18).

- OCR  : CER (Character Error Rate), WER (Word Error Rate) ;
- classification : accuracy, precision, recall, F1 (macro et pondérée),
  matrice de confusion ;
- opérations : taux de revue, taux d'erreurs critiques (sentiment faux),
  latence moyenne.

Aucune valeur n'est inventée : les chiffres proviennent des expériences
réellement exécutées (voir scripts/run_evaluation.py).
"""
from __future__ import annotations

from collections import Counter


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def levenshtein(a: str, b: str) -> int:
    """Distance d'édition entre deux chaînes (DP)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,  # suppression
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (char_a != char_b),  # substitution
                )
            )
        previous = current
    return previous[-1]


def _normalize(text: str) -> str:
    """Minuscules ; la ponctuation est conservée pour le CER et ignorée pour le WER."""
    return text.strip().lower()


def cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate : distance d'édition / longueur de référence."""
    ref = _normalize(reference)
    hyp = _normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


_PUNCTUATION = ".,;:!?()[]{}«»\"'"


def _words(text: str) -> list[str]:
    """Découpe en mots en retirant la ponctuation (les apostrophes internes restent)."""
    tokens = _normalize(text).replace("\n", " ").split()
    return [w.strip(_PUNCTUATION) for w in tokens if any(c.isalnum() for c in w.strip(_PUNCTUATION))]


def wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate : distance d'édition sur les mots / nombre de mots de référence."""
    ref_words = _words(reference)
    hyp_words = _words(hypothesis)
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return levenshtein(ref_words, hyp_words) / len(ref_words)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[tuple[str, str], int]:
    """Compte les paires (réel, prédit)."""
    matrix = Counter(zip(y_true, y_pred))
    return {(t, p): matrix.get((t, p), 0) for t in labels for p in labels}


def compute_classification_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Accuracy, precision/rappel/F1 par classe + moyennes macro et pondérée."""
    matrix = confusion_matrix(y_true, y_pred, labels)
    total = len(y_true) or 1

    per_label: dict[str, dict] = {}
    for label in labels:
        tp = matrix[(label, label)]
        fp = sum(matrix[(other, label)] for other in labels if other != label)
        fn = sum(matrix[(label, other)] for other in labels if other != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }

    supports = [per_label[l]["support"] for l in labels]
    total_support = sum(supports) or 1

    def _macro(key: str) -> float:
        return sum(per_label[l][key] for l in labels) / len(labels) if labels else 0.0

    def _weighted(key: str) -> float:
        return sum(per_label[l][key] * per_label[l]["support"] for l in labels) / total_support

    correct = sum(matrix[(l, l)] for l in labels)
    return {
        "accuracy": round(correct / total, 4),
        "per_label": per_label,
        "macro": {key: round(_macro(key), 4) for key in ("precision", "recall", "f1")},
        "weighted": {key: round(_weighted(key), 4) for key in ("precision", "recall", "f1")},
        "confusion_matrix": {f"{t}->{p}": matrix[(t, p)] for t in labels for p in labels if matrix[(t, p)] > 0},
    }


def error_rate(y_true: list[str], y_pred: list[str]) -> float:
    """Taux d'erreurs critiques : fraction de sentiments mal prédits."""
    if not y_true:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if t != p) / len(y_true)