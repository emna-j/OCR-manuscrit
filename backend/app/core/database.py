"""Accès à la base de données (SQLAlchemy 2.0).

- `Base` : classe déclarative commune, avec convention de nommage
  des contraintes (requise par Alembic pour des migrations reproductibles).
- `engine` / `SessionLocal` : construits depuis la configuration centralisée.
- `get_db` : dépendance FastAPI fournissant une session par requête.

Les tests remplacent `get_db` par une base SQLite en mémoire
(voir tests/conftest.py) — les modèles restent portables entre dialectes.
"""
from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : session ouverte par requête, fermée à la fin."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()