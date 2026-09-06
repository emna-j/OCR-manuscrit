"""Revue humaine (Human-in-the-loop, Phase 9).

Le reviewer peut corriger la transcription, modifier le sentiment ou la
catégorie, ajouter un commentaire, valider ou rejeter le document.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.analysis import HumanReview, ReviewDecision
from app.models.audit_log import AuditEvent
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.schemas.review import ReviewRequest, ReviewResponse
from app.services.audit_service import record_event

router = APIRouter(prefix="/documents", tags=["review"])

_REVIEWABLE_STATES = {
    DocumentStatus.ANALYZED,
    DocumentStatus.COMPLETED,
    DocumentStatus.REQUIRES_REVIEW,
}


@router.post("/{document_id}/review", response_model=ReviewResponse)
def review_document(
    document_id: uuid.UUID,
    body: ReviewRequest,
    request: Request,
    user: User = Depends(require_roles(UserRole.REVIEWER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    from app.api.documents import _get_visible_document

    document = _get_visible_document(db, user, document_id)
    if document.status not in _REVIEWABLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document cannot be reviewed in status {document.status.value}",
        )

    # Persiste la revue.
    review = HumanReview(
        document_id=document.id,
        reviewer_id=user.id,
        corrected_text=body.corrected_text,
        corrected_sentiment=body.corrected_sentiment,
        corrected_category=body.corrected_category,
        comment=body.comment,
        decision=body.decision,
    )
    db.add(review)

    # Applique les corrections au résultat d'analyse (source de vérité finale).
    if document.analysis is not None:
        if body.corrected_text is not None:
            document.analysis.extracted_text = body.corrected_text
        if body.corrected_sentiment is not None:
            document.analysis.sentiment = body.corrected_sentiment
        if body.corrected_category is not None:
            document.analysis.category = body.corrected_category

    if body.decision == ReviewDecision.VALIDATED:
        document.status = DocumentStatus.REVIEWED
    else:
        document.status = DocumentStatus.FAILED
        document.error_reason = "Rejected by reviewer"
    db.commit()
    db.refresh(review)

    record_event(
        db, AuditEvent.HUMAN_REVIEW, user_id=user.id, document_id=document.id,
        details={"decision": body.decision.value},
        ip_address=request.client.host if request.client else None,
    )
    return ReviewResponse(
        id=str(review.id),
        document_id=str(review.document_id),
        decision=review.decision,
        comment=review.comment,
        corrected_text=review.corrected_text,
        corrected_sentiment=review.corrected_sentiment,
        corrected_category=review.corrected_category,
    )