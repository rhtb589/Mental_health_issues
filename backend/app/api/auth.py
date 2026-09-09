"""Auth endpoints: register, login, logout.

Login/logout are audit-logged (requirement: Audit Logging)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import LoginRequest, TokenPair, UserRegister, UserPublic
from app.security.authentication import create_access_token, create_refresh_token, decode_token
from app.security.authorization import Role
from app.security.permissions import get_current_principal, Principal
from app.services import auth_service, audit_service
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    try:
        user = auth_service.create_user(
            db,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            preferred_language=payload.preferred_language,
            user_timezone=payload.timezone,
            prefers_de_identified=payload.prefers_de_identified,
            data_residency_region=payload.data_residency_region,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    audit_service.log_login(db, user.user_id)
    db.commit()
    return TokenPair(
        access_token=create_access_token(user.user_id, user.role),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
):
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            audit_service.log_logout(db, payload["sub"])
            db.commit()
        except Exception:
            pass
    return {"detail": "ok"}
