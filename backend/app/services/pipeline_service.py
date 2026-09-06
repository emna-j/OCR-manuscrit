"""Orchestration du pipeline d'analyse (Phases 3-9).

Machine d'états (cahier des charges §23) :
UPLOADED → PREPROCESSING → OCR_PROCESSING → TEXT_EXTRACTED → ANALYZING
→ ANALYZED → COMPLETED | REQUIRES_REVIEW → REVIEWED
Toute erreur → FAILED (raison générique côté utilisateur, détails en logs).
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.analysis import Analysis, PIIDetection, Sentiment
from app.models.audit_log import AuditEvent
from app.models.document import Document, DocumentStatus
from app.services import gemini_service, pii_service, preprocessing_service, quality_service
from app.services.audit_service import record_event
from app.services.storage_service import get_storage

logger = get_logger()


class PipelineError(Exception):
    """Échec du pipeline — message générique pour l'utilisateur.

    `detail` est le message HTTP exposé au client : générique par défaut
    ("Analysis failed"), plus précis pour les causes connues (quota Gemini).
    """

    def __init__(self, message: str = "Document processing failed", detail: str = "Analysis failed") -> None:
        super().__init__(message)
        self.detail = detail


def _quota_exhausted(exc: Exception) -> bool:
    """Vrai si la cause racine est un dépassement de quota (429 RESOURCE_EXHAUSTED)."""
    cause: Exception | None = exc
    while cause is not None:
        if getattr(cause, "code", None) == 429:
            return True
        message = str(cause)
        if "429" in message or "RESOURCE_EXHAUSTED" in message:
            return True
        cause = cause.__cause__
    return False


def _set_status(db: Session, document: Document, status: DocumentStatus, error_reason: str | None = None) -> None:
    document.status = status
    if error_reason is not None:
        document.error_reason = error_reason
    db.commit()


def run_analysis_pipeline(db: Session, document: Document, force: bool = False) -> Analysis:
    """Exécute le pipeline complet et retourne l'analyse persistée.

    Une seule analyse par document (contrainte unique document_id) :
    si une analyse existe déjà (run précédent échoué ou ré-analyse),
    elle est réutilisée et réinitialisée.

    Économie de quota Gemini : si le document est déjà dans un état final
    avec une analyse exploitable (texte extrait présent) et que `force`
    est faux, l'analyse existante est retournée immédiatement, sans aucun
    appel Gemini. `force=True` relance réellement l'analyse de zéro.
    """
    # Requête explicite (pas `document.analysis`) : la relation peut être
    # périmée dans la session (cache de None avec expire_on_commit=False).
    analysis = db.scalar(select(Analysis).where(Analysis.document_id == document.id))

    # Cache idempotent : analyse déjà complète sans relance explicitée.
    if (
        not force
        and analysis is not None
        and analysis.extracted_text
        and document.status in {DocumentStatus.ANALYZED, DocumentStatus.COMPLETED, DocumentStatus.REQUIRES_REVIEW}
    ):
        logger.info(f"analysis_cached document_id={document.id} status={document.status.value}")
        return analysis

    if analysis is None:
        analysis = Analysis(document_id=document.id)
        db.add(analysis)
        try:
            db.commit()
        except IntegrityError:
            # Course (double-clic, relance simultanée) : une autre requête a
            # créé la ligne entre-temps → on réutilise la ligne existante.
            db.rollback()
            analysis = db.scalar(select(Analysis).where(Analysis.document_id == document.id))
            if analysis is None:
                raise
    else:
        # Ré-analyse : la réinitialisation des résultats (PII, champs) est
        # décalée après la nouvelle extraction (étape 2) afin de conserver
        # la dernière bonne analyse si le run échoue (quota, réseau...).
        pass

    try:
        # 1. Prétraitement (Phase 4).
        storage = get_storage()
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

        # Extraction réussie : on peut maintenant remplacer le run précédent.
        # (En cas d'échec avant cette étape, l'analyse précédente est conservée.)
        for detection in list(analysis.pii_detections):
            db.delete(detection)
        analysis.extracted_text = None
        analysis.lines = None
        analysis.ocr_confidence = None
        analysis.sentiment = None
        analysis.sentiment_confidence = None
        analysis.emotions = None
        analysis.category = None
        analysis.keywords = None
        analysis.summary = None
        analysis.analysis_confidence = None
        document.language = None

        analysis.extracted_text = extraction.text
        analysis.lines = extraction.lines
        analysis.ocr_confidence = extraction.overall_confidence
        document.language = extraction.language
        db.commit()
        _set_status(db, document, DocumentStatus.TEXT_EXTRACTED)

        # 3. PII + anonymisation (Phase 8).
        # Le complément NER Gemini est optionnel (PII_USE_GEMINI) : il ajoute
        # PERSON/ADDRESS/ORGANIZATION/LOCATION mais consomme 1 requête de plus.
        spans = pii_service.detect_all(extraction.text, use_gemini=settings.pii_use_gemini)
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
        if _quota_exhausted(exc):
            raise PipelineError(
                "Gemini quota exceeded",
                detail="Analysis failed: Gemini quota exceeded, please retry later",
            ) from exc
        raise PipelineError("Document processing failed") from exc