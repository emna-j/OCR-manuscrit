"""Sécurité applicative : hachage des mots de passe (bcrypt) et JWT.

Aucun secret n'est stocké en dur : tout provient de la configuration
centralisée (variables d'environnement / .env).
"""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

# bcrypt limite les mots de passe à 72 octets.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """Hache un mot de passe en clair (bcrypt, sel aléatoire)."""
    return bcrypt.hashpw(password.encode("utf-8")[:_MAX_PASSWORD_BYTES], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe en clair contre un hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_MAX_PASSWORD_BYTES], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str | uuid.UUID, role: str) -> str:
    """Crée un JWT signé avec une date d'expiration."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Décode et valide un JWT. Lève jwt.PyJWTError si invalide/expiré."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])