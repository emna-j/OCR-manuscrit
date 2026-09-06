"""Orchestration du pipeline d'analyse (Phases 3-9).

Machine d'états (cahier des charges §23) :
UPLOADED → PREPROCESSING → OCR_PROCESSING → TEXT_EXTRACTED → ANALYZING
→ ANALYZED → COMPLETED | REQUIRES_REVIEW → REVIEWED
Toute erreur → FAILED (raison générique côté utilisateur, détails en logs).
"""
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.analysis import Analysis, PIIDetection, Sentiment
from app.models.audit_log import AuditEvent
from app.models.document import Document, DocumentStatus
from app.services import gemini_service, pii_service, preprocessing_service, quality_service
from app.services.audit_service import record_event
from app.services.storage_service import get_storage

logger = get_logger()


class PipelineError(Exception):
    """Échec du pipeline — message générique pour l'utilisateur."""


def _set_status(db: Session, document: Document, status: DocumentStatus, error_reason: str | None = None) -> None:
    document.status = status
    if error_reason is not None:
        document.error_reason = error_reason
    db.commit()


def run_analysis_pipeline(db: Session, document: Document) -> Analysis:
    """Exécute le pipeline complet et retourne l'analyse persistée."""
    storage = get_storage()
    analysis = Analysis(document_id=document.id)
    db.add(analysis)
    db.commit()

    try:
        # 1. Prétraitement (Phase 4).
        _set_status(db, document, DocumentStatus.PREPROCESSING)
        raw = storage.load(document.stored_filename)
        pages = preprocessing_service.prepare_document_pages(raw, document.content_type)
        logger.info(f"preprocessing_done pages={len(pages)}")

        # 2. Extraction Gemini (Phases 5-6).
        _set_status(db, document, DocumentStatus.OCR_PROCESSING)
        record_event(db, AuditEvent.AI_REQUEST, user_id=document.owner_id, document_id=document.id,
                     details={"stage": "extraction"})
        extraction = gemini_service.extract_manuscript(pages)
        record_event(db, AuditEvent.AI_RESPONSE_STATUS, user_id=document.owner_id, document_id=document.id,
                     details={"stage": "extraction", "status": "success"})

        analysis.extracted_text = extraction.text
        analysis.lines = extraction.lines
        analysis.ocr_confidence = extraction.overall_confidence
        document.language = extraction.language
        db.commit()
        _set_status(db, document, DocumentStatus.TEXT_EXTRACTED)

        # 3. PII + anonymisation (Phase 8).
        spans = pii_service.detect_all(extraction.text, use_gemini=True)
        anonymized = pii_service.anonymize(extraction.text, spans)
        for span in spans:
            db.add(
                PIIDetection(
                    analysis_id=analysis.id,
                    pii_type=span.pii_type,
                    value=span.value,
                    start=span.start,
                    end=span.end,
                    confidence=span.confidence,
                )
            )
        db.commit()
        record_event(db, AuditEvent.PII_DETECTION, user_id=document.owner_id, document_id=document.id,
                     details={"count": len(spans)})

        # 4. Analyse sémantique du texte anonymisé (Phase 7).
        _set_status(db, document, DocumentStatus.ANALYZING)
        record_event(db, AuditEvent.AI_REQUEST, user_id=document.owner_id, document_id=document.id,
                     details={"stage": "analysis"})
        result = gemini_service.analyze_text(anonymized)
        record_event(db, AuditEvent.AI_RESPONSE_STATUS, user_id=document.owner_id, document_id=document.id,
                     details={"stage": "analysis", "status": "success"})

        try:
            analysis.sentiment = Sentiment(result.sentiment)
        except ValueError:
            analysis.sentiment = None
        analysis.sentiment_confidence = result.sentiment_confidence
        analysis.emotions = result.emotions
        analysis.category = result.category
        analysis.keywords = result.keywords
        analysis.summary = result.summary
        analysis.analysis_confidence = result.sentiment_confidence  # proxy documenté
        db.commit()
        _set_status(db, document, DocumentStatus.ANALYZED)

        # 5. Contrôle qualité (Phase 9).
        decision = quality_service.evaluate(
            ocr_confidence=extraction.overall_confidence,
            analysis_confidence=result.sentiment_confidence,
            sentiment=result.sentiment,
        )
        final_status = DocumentStatus.REQUIRES_REVIEW if decision.requires_review else DocumentStatus.COMPLETED
        _set_status(db, document, final_status)

        record_event(db, AuditEvent.DOCUMENT_ANALYSIS, user_id=document.owner_id, document_id=document.id,
                     details={"status": final_status.value, "reasons": decision.reasons})
        return analysis

    except PipelineError:
        raise
    except Exception as exc:
        logger.error(f"pipeline_failed {type(exc).__name__}: {exc}")
        _set_status(db, document, DocumentStatus.FAILED, error_reason="Processing failed")
        raise PipelineError("Document processing failed") from exc