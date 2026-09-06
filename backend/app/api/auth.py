"""Authentification : login JWT et profil courant."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models.audit_log import AuditEvent
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.audit_service import record_event

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = body.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))

    if user is None or user.hashed_password is None or not verify_password(body.password, user.hashed_password):
        # Événement d'audit sans révéler si l'email existe.
        record_event(db, AuditEvent.LOGIN, details={"status": "failed"}, ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token(user.id, user.role.value)
    record_event(db, AuditEvent.LOGIN, user_id=user.id, details={"status": "success"}, ip_address=request.client.host if request.client else None)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user