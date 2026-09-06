"""Endpoints d'analyse : déclenchement du pipeline et lecture du résultat."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.schemas.analysis import AnalysisRead
from app.services.pipeline_service import PipelineError, run_analysis_pipeline

router = APIRouter(prefix="/documents", tags=["analysis"])

# États pendant lesquels une nouvelle analyse est refusée.
_PROCESSING_STATES = {
    DocumentStatus.VALIDATING,
    DocumentStatus.PREPROCESSING,
    DocumentStatus.OCR_PROCESSING,
    DocumentStatus.TEXT_EXTRACTED,
    DocumentStatus.ANALYZING,
}


@router.post("/{document_id}/analyze", response_model=AnalysisRead)
def analyze_document(
    document_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> AnalysisRead:
    from app.api.documents import _get_visible_document

    document = _get_visible_document(db, user, document_id)
    if document.status in _PROCESSING_STATES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is already being processed")

    try:
        analysis = run_analysis_pipeline(db, document)
    except PipelineError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analysis failed")

    db.refresh(analysis)
    return analysis


@router.get("/{document_id}/analysis", response_model=AnalysisRead)
def get_analysis(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisRead:
    from app.api.documents import _get_visible_document

    document = _get_visible_document(db, user, document_id)
    if document.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return document.analysis