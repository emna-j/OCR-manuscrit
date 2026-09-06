"""Journal d'audit (cahier des charges §17).

Enregistre les événements métier et de sécurité. Les logs d'audit ne
contiennent jamais de secrets ni le contenu complet des documents
sensibles — uniquement des références et des métadonnées.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEvent(str, enum.Enum):
    LOGIN = "LOGIN"
    UPLOAD = "UPLOAD"
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    PII_DETECTION = "PII_DETECTION"
    AI_REQUEST = "AI_REQUEST"
    AI_RESPONSE_STATUS = "AI_RESPONSE_STATUS"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    DOCUMENT_DELETION = "DOCUMENT_DELETION"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True, nullable=True
    )
    event: Mapped[AuditEvent] = mapped_column(
        Enum(AuditEvent, native_enum=False, length=30), nullable=False
    )
    # Métadonnées non sensibles (durée, statut, identifiants...) — jamais de contenu complet.
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )