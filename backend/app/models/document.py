"""Modèle document et machine d'états (cahier des charges §23).

`stored_filename` désigne la clé de l'objet dans MinIO (Phase 3/16) :
les binaires ne sont jamais stockés en base.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PREPROCESSING = "PREPROCESSING"
    OCR_PROCESSING = "OCR_PROCESSING"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    COMPLETED = "COMPLETED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    REVIEWED = "REVIEWED"
    FAILED = "FAILED"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)  # clé MinIO (Phase 3/16)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
    # Raison d'erreur générique pour l'utilisateur ; les détails sont dans les logs sécurisés.
    error_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="documents")  # noqa: F821
    analysis: Mapped["Analysis | None"] = relationship(  # noqa: F821
        back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    reviews: Mapped[list["HumanReview"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )