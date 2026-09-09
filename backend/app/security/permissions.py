"""Permission constants and FastAPI dependencies for RBAC enforcement.

These helpers turn the role matrix (see authorization.Role) into reusable
dependencies and guards used by the API layer.
"""
from __future__ import annotations

import abc
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.authorization import Role, is_privileged_role
from app.security.authentication import decode_token

_bearer = HTTPBearer(auto_error=True)


# Coarse permission verbs used across the app.
class Action:
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    MANAGE_ROLES = "manage_roles"
    ACCESS_RAW = "access_raw"          # access to identifiable sensitive data
    ACCESS_AGGREGATE = "access_aggregate"  # anonymized / aggregated only


# Role -> allowed actions on *other* users' sensitive data.
_PRIVILEGED_ACTIONS: dict[Role, set[str]] = {
    Role.ADMIN: {Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE,
                 Action.EXPORT, Action.MANAGE_ROLES, Action.ACCESS_RAW},
    Role.CLINICIAN: {Action.VIEW, Action.CREATE, Action.UPDATE,
                     Action.EXPORT, Action.ACCESS_RAW},
    Role.CARE_COORDINATOR: {Action.VIEW, Action.UPDATE, Action.ACCESS_RAW},
    Role.RESEARCHER: {Action.VIEW, Action.EXPORT, Action.ACCESS_AGGREGATE},
}


def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> "Principal":
    """Validate the bearer token and load the acting principal (user + role)."""
    from app.models.user import User

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
        ) from exc

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown principal")

    return Principal(user_id=user.user_id, role=Role(user.role), is_active=user.is_active)


class Principal:
    """The authenticated actor making a request."""

    def __init__(self, user_id: str, role: Role, is_active: bool = True) -> None:
        self.user_id = user_id
        self.role = role
        self.is_active = is_active

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_researcher(self) -> bool:
        return self.role == Role.RESEARCHER

    def can(self, action: str) -> bool:
        if self.role == Role.PATIENT:
            return False  # patients are governed by ownership, not blanket actions
        return action in _PRIVILEGED_ACTIONS.get(self.role, set())

    def require(self, action: str) -> None:
        if not self.can(action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.role}' cannot perform '{action}'",
            )


def require_role(*roles: Role):
    """Dependency factory: require one of the given roles."""

    def _dep(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in roles]}",
            )
        return principal

    return _dep


def require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return principal
