"""Schémas Pydantic — analyse, PII et revue humaine."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.analysis import PIIType, ReviewDecision, Sentiment


class PIIDetectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pii_type: PIIType
    value: str
    start: int | None = None
    end: int | None = None
    confidence: float | None = None


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    extracted_text: str | None = None
    ocr_confidence: float | None = None
    sentiment: Sentiment | None = None
    sentiment_confidence: float | None = None
    emotions: list | None = None
    category: str | None = None
    keywords: list | None = None
    summary: str | None = None
    analysis_confidence: float | None = None
    created_at: datetime
    pii_detections: list[PIIDetectionRead] = []


class HumanReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    reviewer_id: uuid.UUID | None = None
    corrected_text: str | None = None
    corrected_sentiment: Sentiment | None = None
    corrected_category: str | None = None
    comment: str | None = None
    decision: ReviewDecision
    created_at: datetime