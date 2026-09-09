"""Audit log endpoints.

Provides paginated access to audit logs (admin only).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.permissions import require_admin, Principal
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.occurred_at.desc())
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "event_id": r.event_id,
            "seq": r.seq,
            "event_type": r.event_type,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
            "actor_user_id": r.actor_user_id,
            "subject_user_id": r.subject_user_id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "metadata_json": r.metadata_json,
        }
        for r in rows
    ]
