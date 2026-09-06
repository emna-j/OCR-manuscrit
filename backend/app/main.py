"""Point d'entrée FastAPI.

Lancement (depuis backend/) :
    uvicorn app.main:app --reload

La migration du schéma se fait via Alembic (`alembic upgrade head`) —
l'application ne crée pas les tables elle-même.

Sécurité :
- les erreurs non gérées renvoient un message générique, jamais de stack trace ;
- les détails techniques vont dans les logs structurés (JSON, masqués).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware

setup_logging()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"application_startup environment={settings.environment}")
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Plateforme sécurisée d'analyse de documents manuscrits (Gemini VLM).",
    lifespan=lifespan,
)

# Ordre des middlewares : le rate limiting voit les requêtes en dernier recours.
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ne jamais exposer de stack trace au client (cahier des charges §12)."""
    logger.error(f"unhandled_exception path={request.url.path} type={type(exc).__name__}", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api_router, prefix="/api")