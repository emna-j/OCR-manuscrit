"""Fixtures de test.

- Base SQLite en mémoire (StaticPool) : aucun PostgreSQL requis.
- Stockage local dans un répertoire temporaire (pas de MinIO en test).
- Helpers d'authentification (création d'utilisateurs, jetons).
"""
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def _local_storage(tmp_path: Path) -> None:
    """Force le stockage local dans un répertoire temporaire pour tous les tests."""
    settings.storage_backend = "local"
    settings.storage_local_dir = str(tmp_path / "uploads")


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Vide les compteurs du rate limiter entre chaque test."""
    from app.core.middleware import RateLimitMiddleware

    RateLimitMiddleware.reset()
    yield
    RateLimitMiddleware.reset()


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = testing_session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db_session: Session):
    """Fabrique un utilisateur et retourne (user, headers JWT)."""

    def _factory(role: UserRole = UserRole.USER, email: str | None = None) -> tuple[User, dict[str, str]]:
        user_email = email or f"{role.value.lower()}-{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=user_email,
            hashed_password=hash_password("test-password"),
            full_name=f"Test {role.value}",
            role=role,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        token = create_access_token(user.id, user.role.value)
        return user, {"Authorization": f"Bearer {token}"}

    return _factory


@pytest.fixture
def mock_gemini(monkeypatch):
    """Remplace les appels Gemini par des réponses contrôlées (tests offline)."""

    def _install(
        extraction_text: str = "Bonjour, ceci est un document de test.",
        ocr_confidence: float = 0.92,
        sentiment: str = "neutral",
        sentiment_confidence: float = 0.85,
        category: str = "note",
        keywords: list[str] | None = None,
        entities: list[dict] | None = None,
    ):
        from app.services import gemini_service

        def fake_extract(images, mime_type="image/png"):
            return gemini_service.ExtractionResult(
                language="fr",
                text=extraction_text,
                lines=[{"text": extraction_text, "confidence": ocr_confidence}],
                overall_confidence=ocr_confidence,
                uncertain_segments=[],
            )

        def fake_analyze(text):
            return gemini_service.AnalysisResult(
                sentiment=sentiment,
                sentiment_confidence=sentiment_confidence,
                emotions=[{"label": "calm", "confidence": 0.6}],
                category=category,
                keywords=keywords or ["test"],
                summary="Résumé de test.",
            )

        monkeypatch.setattr(gemini_service, "extract_manuscript", fake_extract)
        monkeypatch.setattr(gemini_service, "analyze_text", fake_analyze)
        monkeypatch.setattr(gemini_service, "detect_entities", lambda text: entities or [])

    return _install