"""Crée le compte administrateur initial.

Usage (depuis backend/) :
    python -m app.seed

Lit ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_FULL_NAME dans la configuration
(.env ou variables d'environnement). Sans effet si le compte existe déjà.
"""
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def seed_admin() -> User | None:
    if not settings.admin_email or not settings.admin_password:
        print("ADMIN_EMAIL/ADMIN_PASSWORD non définis — aucun compte créé.")
        return None

    db = SessionLocal()
    try:
        email = settings.admin_email.lower().strip()
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"Compte administrateur déjà présent : {email}")
            return existing

        admin = User(
            email=email,
            hashed_password=hash_password(settings.admin_password),
            full_name=settings.admin_full_name or "Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Compte administrateur créé : {email}")
        return admin
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()