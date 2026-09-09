"""Assignment endpoints.

Lists provider-patient assignments (admin).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.permissions import require_admin, Principal
from app.models.assignment import Assignment

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("")
def list_assignments(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    active_only: bool = Query(default=True),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(Assignment).order_by(Assignment.created_at.desc())
    if active_only:
        stmt = stmt.where(Assignment.active.is_(True))
    stmt = stmt.offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "assignment_id": r.assignment_id,
            "patient_id": r.patient_id,
            "provider_id": r.provider_id,
            "provider_role": r.provider_role,
            "active": r.active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "created_by": r.created_by,
        }
        for r in rows
    ]
