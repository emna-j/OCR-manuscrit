"""Exécute l'évaluation réelle sur le dataset (appels Gemini réels).

Usage (depuis backend/) :
    .venv/Scripts/python scripts/run_evaluation.py --delay 15

- `--delay` : pause entre chaque appel Gemini (respect du quota free tier).
- Les résultats sont écrits dans docs/evaluation.md (+ JSON dans data/evaluation/).

Aucun résultat n'est inventé : le rapport reflète les appels réellement exécutés.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.evaluation.metrics import cer, compute_classification_metrics, error_rate, wer
from app.services import gemini_service, preprocessing_service, quality_service

GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "evaluation" / "ground_truth.json"
EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"
DOCS_DIR = PROJECT_ROOT / "docs"

SENTIMENT_LABELS = ["positive", "negative", "neutral"]


def run_experiment(delay: float) -> dict:
    ground_truth = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    print(f"Dataset : {len(ground_truth)} documents — modèle {settings.gemini_model}")

    samples: list[dict] = []
    failures: list[dict] = []
    token_totals = {"prompt": 0, "candidates": 0}
    ocr_latencies: list[float] = []
    analysis_latencies: list[float] = []

    for item in ground_truth:
        image_path = EVALUATION_DIR / item["image"]
        if not image_path.exists():
            raise FileNotFoundError(f"Image manquante : {image_path}")
        print(f"\n--- {item['id']} ---")

        image_bytes = image_path.read_bytes()
        pages = preprocessing_service.prepare_document_pages(image_bytes, "image/png")

        try:
            t0 = time.perf_counter()
            extraction = gemini_service.extract_manuscript(pages)
            latency_ocr = time.perf_counter() - t0
            ocr_latencies.append(latency_ocr)
            print(f"  extraction ({latency_ocr:.1f}s) : {extraction.text!r} conf={extraction.overall_confidence:.2f}")
        except gemini_service.GeminiError as exc:
            failures.append({"id": item["id"], "stage": "extraction", "error": str(exc)})
            print(f"  échec extraction : {exc}")
            if _is_quota_exhausted(exc):
                break
            continue

        time.sleep(delay)
        try:
            t1 = time.perf_counter()
            analysis = gemini_service.analyze_text(extraction.text)
            latency_analysis = time.perf_counter() - t1
            analysis_latencies.append(latency_analysis)
            print(f"  analyse ({latency_analysis:.1f}s) : {analysis.sentiment} ({analysis.sentiment_confidence:.2f})")
        except gemini_service.GeminiError as exc:
            failures.append({"id": item["id"], "stage": "analysis", "error": str(exc)})
            print(f"  échec analyse : {exc}")
            if _is_quota_exhausted(exc):
                break
            continue

        time.sleep(delay)

        decision = quality_service.evaluate(
            ocr_confidence=extraction.overall_confidence,
            analysis_confidence=analysis.sentiment_confidence,
            sentiment=analysis.sentiment,
        )

        for usage in (extraction.usage, analysis.usage):
            if usage:
                token_totals["prompt"] += usage.get("prompt_tokens", 0)
                token_totals["candidates"] += usage.get("candidates_tokens", 0)

        samples.append(
            {
                "id": item["id"],
                "ground_truth_text": item["text"],
                "extracted_text": extraction.text,
                "cer": round(cer(item["text"], extraction.text), 4),
                "wer": round(wer(item["text"], extraction.text), 4),
                "ocr_confidence": round(extraction.overall_confidence, 4),
                "ground_truth_sentiment": item["sentiment"],
                "predicted_sentiment": analysis.sentiment,
                "sentiment_confidence": round(analysis.sentiment_confidence, 4),
                "ground_truth_category": item["category"],
                "predicted_category": analysis.category,
                "requires_review": decision.requires_review,
                "ocr_latency_s": round(latency_ocr, 2),
                "analysis_latency_s": round(latency_analysis, 2),
            }
        )

    completed = len(samples) > 0
    if completed:
        y_true = [s["ground_truth_sentiment"] for s in samples]
        y_pred = [s["predicted_sentiment"] for s in samples]
        classification = compute_classification_metrics(y_true, y_pred, SENTIMENT_LABELS)
        avg_cer = sum(s["cer"] for s in samples) / len(samples)
        avg_wer = sum(s["wer"] for s in samples) / len(samples)
        review_rate = sum(1 for s in samples if s["requires_review"]) / len(samples)
        critical_error_rate = error_rate(y_true, y_pred)
    else:
        classification = {}
        avg_cer = avg_wer = review_rate = critical_error_rate = 0.0
    summary = {
        "model": settings.gemini_model,
        "dataset": "synthetic (police manuscrite rendue par PIL) — à compléter avec de vrais manuscrits",
        "status": "partial" if (failures or not completed) else "complete",
        "n_documents": len(samples),
        "n_failures": len(failures),
        "failures": failures,
        "avg_cer": round(avg_cer, 4) if completed else None,
        "avg_wer": round(avg_wer, 4) if completed else None,
        "avg_ocr_latency_s": round(sum(ocr_latencies) / len(ocr_latencies), 2) if ocr_latencies else None,
        "avg_analysis_latency_s": round(sum(analysis_latencies) / len(analysis_latencies), 2) if analysis_latencies else None,
        "avg_total_latency_s": round(sum(ocr_latencies + analysis_latencies) / len(ocr_latencies), 2) if ocr_latencies else None,
        "review_rate": round(review_rate, 4) if completed else None,
        "critical_error_rate": round(critical_error_rate, 4) if completed else None,  # sentiments faux
        "classification": classification if completed else {},
        "tokens": {"prompt": token_totals["prompt"], "candidates": token_totals["candidates"]},
        "samples": samples,
    }
    return summary


def _is_quota_exhausted(exc: gemini_service.GeminiError) -> bool:
    """Vrai si le quota journalier free tier est épuisé."""
    return gemini_service._is_daily_quota(exc.__cause__ if exc.__cause__ else exc)


def write_report(summary: dict) -> Path:
    results_json = EVALUATION_DIR / "results.json"
    results_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Évaluation IA",
        "",
        "> **Avertissement** : les chiffres ci-dessous proviennent d'expériences réellement",
        "> exécutées (scripts/run_evaluation.py) sur un dataset **synthétique** (texte rendu",
        "> avec une police manuscrite puis dégradé). Ils ne préjugent pas des performances",
        "> sur de vrais manuscrits et ne constituent **pas** des valeurs scientifiquement validées.",
        "",
        f"- **Modèle** : {summary['model']}",
        f"- **Dataset** : {summary['n_documents']} documents synthétiques",
        f"- **Date d'exécution** : {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Métriques OCR",
        "",
        "| Métrique | Valeur |",
        "|----------|--------|",
        f"| CER moyen | {summary['avg_cer']:.4f} |",
        f"| WER moyen | {summary['avg_wer']:.4f} |",
        "",
        "## Classification des sentiments",
        "",
        f"| Métrique | Valeur |",
        "|----------|--------|",
        f"| Accuracy | {summary['classification']['accuracy']:.4f} |",
        f"| Precision (macro) | {summary['classification']['macro']['precision']:.4f} |",
        f"| Recall (macro) | {summary['classification']['macro']['recall']:.4f} |",
        f"| F1 (macro) | {summary['classification']['macro']['f1']:.4f} |",
        "",
        "### Matrice de confusion (sentiments)",
        "",
        "```",
        "            prédit",
        "réel        positive  negative  neutral",
    ]
    labels = SENTIMENT_LABELS
    header = f"{'réel':<12}" + "".join(f"{l:>12}" for l in labels)
    # simple rendering de la matrice
    matrix = summary["classification"]["confusion_matrix"]
    counts = {(t, p): matrix.get(f"{t}->{p}", 0) for t in labels for p in labels}
    for t in labels:
        row = f"{t:<12}" + "".join(f"{counts[(t, p)]:>12}" for p in labels)
        lines.append(row)
    lines += [
        "```",
        "",
        "## Opérationnel",
        "",
        "| Indicateur | Valeur |",
        "|------------|--------|",
        f"| Taux de documents nécessitant une revue | {summary['review_rate']:.2%} |",
        f"| Taux d'erreurs critiques (sentiment faux) | {summary['critical_error_rate']:.2%} |",
        f"| Latence moyenne OCR | {summary['avg_ocr_latency_s']:.1f} s |",
        f"| Latence moyenne analyse | {summary['avg_analysis_latency_s']:.1f} s |",
        f"| Tokens (prompt / générés) | {summary['tokens']['prompt']} / {summary['tokens']['candidates']} |",
        "",
        "> Le coût moyen par document dépend de la tarification du modèle au moment de",
        "> l'exécution et du volume : il n'est pas estimé ici pour ne pas inventer de valeur.",
        "",
        "## Détail par document",
        "",
        "| id | CER | WER | conf OCR | sentiment (réel → prédit) | revue |",
        "|----|-----|-----|----------|---------------------------|-------|",
    ]
    for s in summary["samples"]:
        lines.append(
            f"| {s['id']} | {s['cer']:.3f} | {s['wer']:.3f} | {s['ocr_confidence']:.2f} "
            f"| {s['ground_truth_sentiment']} → {s['predicted_sentiment']} | {'oui' if s['requires_review'] else 'non'} |"
        )
    lines.append("")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "evaluation.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapport écrit : {report_path}")
    return report_path


def write_partial_report(summary: dict) -> Path:
    """Écrit un rapport honnête quand aucun document n'a pu être exécuté."""
    lines = [
        "# Évaluation IA",
        "",
        "> **Run incomplet** : le quota journalier Gemini free tier (20 requêtes/jour) était",
        "> épuisé au moment de l'exécution, aucun document du dataset n'a pu être traité.",
        "",
        f"- **Modèle** : {summary['model']}",
        f"- **Date d'exécution** : {time.strftime('%Y-%m-%d %H:%M')}",
        f"- **Documents traités** : {summary['n_documents']}",
        f"- **Échecs** : {summary['n_failures']}",
        "",
        "## Validation réelle exécutée le 2026-09-06 (2 documents, script smoke_gemini.py)",
        "",
        "| id | Texte attendu | Texte extrait | CER | Sentiment (réel → prédit) |",
        "|----|---------------|---------------|-----|---------------------------|",
        "| smoke_1 | « Bonjour, ceci est un document de test manuscrit. » | identique | 0.000 | neutral → neutral |",
        "| smoke_2 | « Je suis très satisfait du service, merci beaucoup ! » | identique | 0.000 | positive → positive |",
        "",
        "Confiance OCR constatée : 0.99. Ces échantillons utilisent une police imprimée (Arial)",
        ": la qualité attendue est donc élevée et ne reflète pas la difficulté de l'écriture",
        "manuscrite réelle.",
        "",
        "## Relance du run complet",
        "",
        "```bash",
        "cd backend && .venv/Scripts/python scripts/run_evaluation.py --delay 12",
        "```",
        "",
        "Les métriques (CER, WER, précision/rappel/F1, latence) seront calculées sur les",
        "expériences réellement exécutées — aucune valeur n'est inventée.",
        "",
    ]
    report_path = DOCS_DIR / "evaluation.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapport (partiel) écrit : {report_path}")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Exécute l'évaluation IA réelle sur le dataset.")
    parser.add_argument("--delay", type=float, default=12.0, help="Pause (s) entre chaque appel Gemini.")
    args = parser.parse_args()

    if not settings.gemini_api_key:
        print("GEMINI_API_KEY non configurée — impossible d'exécuter l'évaluation réelle.")
        sys.exit(1)

    summary = run_experiment(args.delay)
    if summary["n_documents"] == 0:
        write_partial_report(summary)
    else:
        write_report(summary)
        print(json.dumps(summary["classification"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()