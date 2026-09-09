"""Data subject request endpoints.

Lists deletion/anonymization requests (admin).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.permissions import require_admin, Principal
from app.models.retention_request import DataSubjectRequest

router = APIRouter(prefix="/data-requests", tags=["data-requests"])


@router.get("")
def list_data_requests(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(DataSubjectRequest).order_by(DataSubjectRequest.requested_at.desc())
    if status_filter:
        stmt = stmt.where(DataSubjectRequest.status == status_filter)
    stmt = stmt.offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "request_id": r.request_id,
            "user_id": r.user_id,
            "request_type": r.request_type,
            "reason": r.reason,
            "status": r.status,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            "processed_by": r.processed_by,
        }
        for r in rows
    ]
