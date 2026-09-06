"""Endpoints documents : upload sécurisé, liste, détail, suppression."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.analysis import HumanReview
from app.models.audit_log import AuditEvent
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.schemas.document import DocumentDetail, DocumentListResponse, DocumentRead
from app.services.audit_service import record_event
from app.services.storage_service import get_storage
from app.services.validation_service import UploadValidationError, validate_upload

router = APIRouter(prefix="/documents", tags=["documents"])

_STAFF_ROLES = (UserRole.ADMIN, UserRole.ANALYST, UserRole.REVIEWER)


def _visible_documents(user: User):
    """Query des documents visibles selon le rôle (RBAC)."""
    if user.role in _STAFF_ROLES:
        return select(Document)
    return select(Document).where(Document.owner_id == user.id)


def _get_visible_document(db: Session, user: User, document_id: uuid.UUID) -> Document:
    document = db.scalar(_visible_documents(user).where(Document.id == document_id))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    data = file.file.read()
    try:
        info = validate_upload(file.filename or "", data)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    document = Document(
        owner_id=user.id,
        original_filename=Path(file.filename or "document").name,
        content_type=info.content_type,
        file_size_bytes=len(data),
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    db.flush()

    storage = get_storage()
    storage_key = f"{document.id}/{Path(file.filename or 'document').name}"
    try:
        storage.save(storage_key, data, info.content_type)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage failed")

    document.stored_filename = storage_key
    db.commit()
    db.refresh(document)

    record_event(
        db, AuditEvent.UPLOAD, user_id=user.id, document_id=document.id,
        details={"size_bytes": len(data), "content_type": info.content_type},
        ip_address=request.client.host if request.client else None,
    )
    return document


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status_filter: DocumentStatus | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    query = _visible_documents(user)
    if status_filter is not None:
        query = query.where(Document.status == status_filter)
    documents = db.scalars(query.order_by(Document.created_at.desc()).limit(100)).all()
    return DocumentListResponse(items=[DocumentRead.model_validate(d) for d in documents], total=len(documents))


@router.get("/{document_id}/file")
def get_document_file(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sert le fichier original (image/PDF) à l'utilisateur autorisé."""
    from fastapi import Response

    document = _get_visible_document(db, user, document_id)
    if not document.stored_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    try:
        data = get_storage().load(document.stored_filename)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return Response(content=data, media_type=document.content_type)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    document = db.scalar(
        _visible_documents(user)
        .where(Document.id == document_id)
        .options(joinedload(Document.analysis), joinedload(Document.reviews))
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    latest_review = (
        db.scalar(
            select(HumanReview)
            .where(HumanReview.document_id == document_id)
            .order_by(HumanReview.created_at.desc())
            .limit(1)
        )
        if document.reviews
        else None
    )
    return DocumentDetail(
        **DocumentRead.model_validate(document).model_dump(),
        analysis=document.analysis,
        latest_review=latest_review,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    request: Request,
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    document = _get_visible_document(db, user, document_id)
    if document.owner_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    if document.stored_filename:
        try:
            get_storage().delete(document.stored_filename)
        except Exception:
            pass  # suppression best-effort, les logs noteront l'échec

    document_id_str = str(document.id)
    db.delete(document)
    db.commit()
    record_event(
        db, AuditEvent.DOCUMENT_DELETION, user_id=user.id,
        details={"document_id": document_id_str},
        ip_address=request.client.host if request.client else None,
    )