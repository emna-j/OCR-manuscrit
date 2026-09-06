"""Statistiques du dashboard (cahier des charges §24)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.analysis import Analysis, Sentiment
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardStatistics, RecentDocument

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_STAFF_ROLES = (UserRole.ADMIN, UserRole.ANALYST, UserRole.REVIEWER)


def _visible_document_ids(user: User) -> select:
    """Sélection des identifiants de documents visibles selon le rôle."""
    query = select(Document.id)
    if user.role not in _STAFF_ROLES:
        query = query.where(Document.owner_id == user.id)
    return query


@router.get("/statistics", response_model=DashboardStatistics)
def get_statistics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStatistics:
    visible_ids_select = _visible_document_ids(user)
    visible_ids_sub = visible_ids_select.subquery()

    total = db.scalar(select(func.count()).select_from(visible_ids_sub)) or 0

    sentiment_counts = dict(
        db.execute(
            select(Analysis.sentiment, func.count())
            .join(Document, Document.id == Analysis.document_id)
            .where(Document.id.in_(visible_ids_select))
            .group_by(Analysis.sentiment)
        ).all()
    )

    averages = db.execute(
        select(func.avg(Analysis.ocr_confidence), func.avg(Analysis.analysis_confidence))
        .join(Document, Document.id == Analysis.document_id)
        .where(Document.id.in_(visible_ids_select))
    ).one()

    review_ids = _visible_document_ids(user).where(Document.status == DocumentStatus.REQUIRES_REVIEW)
    requires_review = db.scalar(select(func.count()).select_from(review_ids.subquery())) or 0

    recent_rows = db.execute(
        select(Document, Analysis.sentiment)
        .outerjoin(Analysis, Analysis.document_id == Document.id)
        .where(Document.id.in_(visible_ids_select))
        .order_by(Document.created_at.desc())
        .limit(5)
    ).all()

    recent = [
        RecentDocument(
            id=doc.id,
            original_filename=doc.original_filename,
            status=doc.status,
            sentiment=sentiment,
            ocr_confidence=doc.analysis.ocr_confidence if doc.analysis else None,
            analysis_confidence=doc.analysis.analysis_confidence if doc.analysis else None,
            created_at=doc.created_at,
        )
        for doc, sentiment in recent_rows
    ]

    return DashboardStatistics(
        total_documents=total,
        positive_count=sentiment_counts.get(Sentiment.POSITIVE, 0),
        negative_count=sentiment_counts.get(Sentiment.NEGATIVE, 0),
        neutral_count=sentiment_counts.get(Sentiment.NEUTRAL, 0),
        unknown_sentiment_count=sentiment_counts.get(None, 0),
        average_ocr_confidence=float(averages[0]) if averages[0] is not None else None,
        average_analysis_confidence=float(averages[1]) if averages[1] is not None else None,
        requires_review_count=requires_review,
        recent_documents=recent,
    )