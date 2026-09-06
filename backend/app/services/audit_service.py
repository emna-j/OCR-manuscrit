"""Journal d'audit (cahier des charges §17, Phase 12).

Enregistre les événements de sécurité et métier dans `audit_logs`.
Ne contient jamais de secrets ni le contenu complet des documents.
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditEvent, AuditLog


def record_event(
    db: Session,
    event: AuditEvent,
    *,
    user_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Ajoute un événement d'audit et le commit immédiatement.

    Un commit dédié garantit que l'événement est persisté même si la
    transaction principale échoue ensuite.
    """
    log = AuditLog(
        user_id=user_id,
        document_id=document_id,
        event=event,
        details=details,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    return log