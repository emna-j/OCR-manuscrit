"""Importe tous les modèles pour que `Base.metadata` (Alembic) les connaisse."""

from app.models.analysis import Analysis, HumanReview, PIIDetection, PIIType, ReviewDecision, Sentiment
from app.models.audit_log import AuditEvent, AuditLog
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole

__all__ = [
    "Analysis",
    "AuditEvent",
    "AuditLog",
    "Document",
    "DocumentStatus",
    "HumanReview",
    "PIIDetection",
    "PIIType",
    "ReviewDecision",
    "Sentiment",
    "User",
    "UserRole",
]