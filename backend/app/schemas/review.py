"""Schémas Pydantic — revue humaine (Human-in-the-loop)."""
from app.models.analysis import ReviewDecision, Sentiment
from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    corrected_text: str | None = None
    corrected_sentiment: Sentiment | None = None
    corrected_category: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=2000)
    decision: ReviewDecision


class ReviewResponse(BaseModel):
    id: str
    document_id: str
    decision: ReviewDecision
    comment: str | None = None
    corrected_text: str | None = None
    corrected_sentiment: Sentiment | None = None
    corrected_category: str | None = None