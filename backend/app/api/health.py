"""Endpoint de santé : vérifie que l'API répond et que la base est joignable.

Sert de base aux healthchecks Docker (Phase 15) et à l'observabilité (§21).
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        database = "connected"
    except Exception as exc:  # la base ne doit pas faire tomber le healthcheck
        logger.warning("health_database_unavailable", extra={"error": str(exc)})
        database = "unavailable"

    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": database,
    }