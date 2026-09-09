"""Authentication / account service.

Handles account creation, credential verification and privileged role changes
(which are audit-logged per the RBAC requirement).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.security.authorization import Role
from app.security.authentication import hash_password, verify_password
from app.models.user import User
from app.services import audit_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_user(
    db: Session,
    email: str,
    password: str,
    *,
    role: str = "patient",
    date_of_birth: datetime | None = None,
    age_group: str | None = None,
    preferred_language: str | None = None,
    user_timezone: str | None = None,
    prefers_de_identified: bool = False,
    data_residency_region: str = "in",
) -> User:
    if role not in [r.value for r in Role]:
        raise ValueError(f"Unknown role: {role}")
    existing = db.execute(select(User).where(User.email == email)).scalars().first()
    if existing:
        raise ValueError("Email already registered")
    user = User(
        user_id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(password),
        role=role,
        date_of_birth=date_of_birth,
        age_group=age_group,
        preferred_language=preferred_language,
        timezone=user_timezone,
        prefers_de_identified=prefers_de_identified,
        data_residency_region=data_residency_region,
        last_active_at=_utcnow(),
    )
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.execute(select(User).where(User.email == email)).scalars().first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    user.last_active_at = _utcnow()
    db.flush()
    return user


def change_role(db: Session, actor_id: str, user_id: str, new_role: str) -> User:
    if new_role not in [r.value for r in Role]:
        raise ValueError(f"Unknown role: {new_role}")
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")
    old_role = user.role
    if old_role == new_role:
        return user
    user.role = new_role
    db.flush()
    audit_service.log_role_change(db, actor=actor_id, subject=user_id, old_role=old_role, new_role=new_role)
    return user
