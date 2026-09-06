"""Modèles d'analyse : résultat d'extraction/analyse, détections PII et revues humaines.

Tables : `document_analysis`, `pii_detections`, `human_reviews`.
Les colonnes JSON stockent des structures simples (lignes, émotions,
mots-clés) sans nécessiter de tables dédiées.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class PIIType(str, enum.Enum):
    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    ID_NUMBER = "ID_NUMBER"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"


class ReviewDecision(str, enum.Enum):
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class Analysis(Base):
    __tablename__ = "document_analysis"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    # Étape A — extraction
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    lines: Mapped[list | None] = mapped_column(JSON, nullable=True)  # lignes + confiance par ligne
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Étape B — analyse
    sentiment: Mapped[Sentiment | None] = mapped_column(
        Enum(Sentiment, native_enum=False, length=10), nullable=True
    )
    sentiment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    emotions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="analysis")  # noqa: F821
    pii_detections: Mapped[list["PIIDetection"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class PIIDetection(Base):
    __tablename__ = "pii_detections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_analysis.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pii_type: Mapped[PIIType] = mapped_column(
        Enum(PIIType, native_enum=False, length=20), nullable=False
    )
    # Valeur détectée (conservée pour la revue humaine ; jamais envoyée aux logs).
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    start: Mapped[int | None] = mapped_column(Integer, nullable=True)  # position dans le texte
    end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analysis: Mapped["Analysis"] = relationship(back_populates="pii_detections")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True  # rempli avec l'auth (Phase 11)
    )
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_sentiment: Mapped[Sentiment | None] = mapped_column(
        Enum(Sentiment, native_enum=False, length=10), nullable=True
    )
    corrected_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, native_enum=False, length=10), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="reviews")  # noqa: F821