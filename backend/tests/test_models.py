"""Tests unitaires des modèles SQLAlchemy et de leurs relations."""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.analysis import Analysis, HumanReview, PIIDetection, PIIType, ReviewDecision, Sentiment
from app.models.audit_log import AuditEvent, AuditLog
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole


def _create_user(db: Session, email: str = "analyst@example.com") -> User:
    user = User(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_user_defaults(db_session: Session) -> None:
    user = _create_user(db_session)
    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.id is not None
    assert isinstance(user.id, uuid.UUID)


def test_document_defaults_and_owner_relationship(db_session: Session) -> None:
    user = _create_user(db_session)
    document = Document(
        owner_id=user.id,
        original_filename="note.jpg",
        content_type="image/jpeg",
        file_size_bytes=1024,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    assert document.status == DocumentStatus.UPLOADED
    assert document in user.documents


def test_full_analysis_chain(db_session: Session) -> None:
    """User -> Document -> Analysis -> PII + HumanReview."""
    user = _create_user(db_session)
    document = Document(
        owner_id=user.id,
        original_filename="letter.png",
        content_type="image/png",
        file_size_bytes=2048,
    )
    db_session.add(document)
    db_session.flush()

    analysis = Analysis(
        document_id=document.id,
        extracted_text="Ahmed Ben Ali peut être contacté au 22123456.",
        ocr_confidence=0.93,
        sentiment=Sentiment.NEGATIVE,
        sentiment_confidence=0.88,
        emotions=[{"label": "frustration", "confidence": 0.9}],
        category="complaint",
        keywords=["service", "problème"],
    )
    db_session.add(analysis)
    db_session.flush()

    pii = PIIDetection(
        analysis_id=analysis.id,
        pii_type=PIIType.PERSON,
        value="Ahmed Ben Ali",
        start=0,
        end=14,
        confidence=0.99,
    )
    db_session.add(pii)
    db_session.flush()

    review = HumanReview(
        document_id=document.id,
        reviewer_id=user.id,
        corrected_text="Texte corrigé.",
        decision=ReviewDecision.VALIDATED,
    )
    db_session.add(review)
    db_session.commit()

    assert document.analysis is analysis
    assert analysis.pii_detections == [pii]
    assert document.reviews == [review]
    assert analysis.document is document


def test_audit_log_creation(db_session: Session) -> None:
    user = _create_user(db_session)
    log = AuditLog(
        user_id=user.id,
        event=AuditEvent.LOGIN,
        details={"method": "password"},
        ip_address="127.0.0.1",
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.event == AuditEvent.LOGIN
    assert log.details == {"method": "password"}


def test_duplicate_email_rejected(db_session: Session) -> None:
    _create_user(db_session, email="dup@example.com")
    with pytest.raises(Exception):  # IntegrityError selon le dialecte
        db_session.add(User(email="dup@example.com"))
        db_session.commit()