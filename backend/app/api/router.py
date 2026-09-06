"""Regroupe tous les routers de l'API sous le préfixe /api."""
from fastapi import APIRouter

from app.api.analysis import router as analysis_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.review import router as review_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(analysis_router)
api_router.include_router(review_router)
api_router.include_router(dashboard_router)