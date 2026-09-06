"""Dépendances FastAPI : authentification (JWT) et autorisation (RBAC)."""
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Retourne l'utilisateur authentifié ou lève 401."""
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise _CREDENTIALS_EXCEPTION
        user = db.get(User, uuid.UUID(user_id))
    except (jwt.PyJWTError, ValueError):
        raise _CREDENTIALS_EXCEPTION
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


def require_roles(*roles: UserRole):
    """Fabrique une dépendance exigeant un des rôles donnés (RBAC)."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency