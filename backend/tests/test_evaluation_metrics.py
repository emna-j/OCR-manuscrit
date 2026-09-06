"""Tests unitaires des métriques d'évaluation (CER/WER, classification)."""
from app.evaluation.metrics import cer, compute_classification_metrics, error_rate, levenshtein, wer


def test_levenshtein_basics() -> None:
    assert levenshtein("", "") == 0
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("abc", "abcd") == 1


def test_cer_exact() -> None:
    assert cer("Bonjour le monde", "Bonjour le monde") == 0.0


def test_cer_perfect_on_empty() -> None:
    assert cer("", "") == 0.0
    assert cer("", "texte") == 1.0


def test_cer_single_typo() -> None:
    assert 0.0 < cer("bonjour", "bonjoue") < 0.2


def test_wer_exact() -> None:
    assert wer("le chat dort", "le chat dort") == 0.0


def test_wer_one_word_wrong() -> None:
    assert wer("le chat dort", "le chien dort") == 1 / 3


def test_wer_ignores_punctuation_case() -> None:
    assert wer("Bonjour, le monde !", "bonjour le monde") == 0.0


def test_classification_metrics_perfect() -> None:
    y_true = ["positive", "negative", "neutral", "positive"]
    y_pred = ["positive", "negative", "neutral", "positive"]
    result = compute_classification_metrics(y_true, y_pred, ["positive", "negative", "neutral"])
    assert result["accuracy"] == 1.0
    assert result["macro"]["f1"] == 1.0


def test_classification_metrics_imperfect() -> None:
    y_true = ["positive", "negative", "negative", "positive"]
    y_pred = ["positive", "negative", "positive", "positive"]
    result = compute_classification_metrics(y_true, y_pred, ["positive", "negative", "neutral"])
    assert result["accuracy"] == 0.75
    assert result["per_label"]["positive"]["precision"] == round(2 / 3, 4)
    assert result["per_label"]["positive"]["recall"] == 1.0


def test_error_rate() -> None:
    assert error_rate(["positive", "negative"], ["positive", "positive"]) == 0.5
    assert error_rate([], []) == 0.0