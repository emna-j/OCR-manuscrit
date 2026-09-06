"""Schémas Pydantic — documents.

Validation stricte des entrées/sorties API. Les enums partagés avec les
modèles garantissent l'alignement entre API et base de données.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus
from app.schemas.analysis import AnalysisRead, HumanReviewRead


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    original_filename: str
    content_type: str
    file_size_bytes: int
    language: str | None = None
    status: DocumentStatus
    error_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int


class DocumentDetail(DocumentRead):
    analysis: AnalysisRead | None = None
    latest_review: HumanReviewRead | None = None