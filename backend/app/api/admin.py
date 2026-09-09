"""Admin endpoints: RBAC management, retention sweep, audit integrity.

All privileged actions here are restricted to the ADMIN role.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.assessment import AssignmentCreate
from app.schemas.user import RoleChangeRequest
from app.security.permissions import require_admin, Principal
from app.services import auth_service, rbac_service, retention_service, audit_service
from app.models.assignment import Assignment
from app.models.retention_request import DataSubjectRequest, RequestStatus

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users/{user_id}/role", status_code=status.HTTP_200_OK)
def change_user_role(
    user_id: str,
    payload: RoleChangeRequest,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        auth_service.change_role(db, principal.user_id, user_id, payload.new_role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.commit()
    return {"detail": "role updated"}


@router.post("/assignments", status_code=status.HTTP_201_CREATED)
def assign_provider(
    payload: AssignmentCreate,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        rbac_service.assign_provider(
            db, payload.patient_id, payload.provider_id, payload.provider_role, principal.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.commit()
    return {"detail": "assigned"}


@router.get("/audit/integrity")
def audit_integrity(
    principal: Principal = Depends(require_admin), db: Session = Depends(get_db)
):
    return audit_service.verify_chain(db)


@router.post("/retention/sweep")
def run_sweep(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    result = retention_service.run_retention_sweep(db)
    db.commit()
    return result


@router.get("/subject-requests")
def list_requests(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(
        select(DataSubjectRequest).where(DataSubjectRequest.status == RequestStatus.PENDING)
    ).scalars().all()
    return [
        {
            "request_id": r.request_id,
            "user_id": r.user_id,
            "request_type": r.request_type,
            "status": r.status,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
        }
        for r in rows
    ]
