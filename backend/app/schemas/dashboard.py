"""Schémas Pydantic — statistiques du dashboard."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.analysis import Sentiment
from app.models.document import DocumentStatus


class RecentDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    status: DocumentStatus
    sentiment: Sentiment | None = None
    ocr_confidence: float | None = None
    analysis_confidence: float | None = None
    created_at: datetime


class DashboardStatistics(BaseModel):
    total_documents: int
    positive_count: int
    negative_count: int
    neutral_count: int
    unknown_sentiment_count: int
    average_ocr_confidence: float | None = None
    average_analysis_confidence: float | None = None
    requires_review_count: int
    recent_documents: list[RecentDocument]