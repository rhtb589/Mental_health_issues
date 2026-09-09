"""User self-service endpoints: profile, and data-subject (erasure) requests.

Requirement (Retention / Consent): users may request deletion or anonymization
of their data at any time. These requests are queued and processed by the
retention service / cleanup worker.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserPublic
from app.security.permissions import get_current_principal, require_admin, Principal
from app.models.retention_request import (
    DataSubjectRequest,
    RequestStatus,
    RequestType,
)
from app.services import audit_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def me(principal: Principal = Depends(get_current_principal), db=Depends(get_db)):
    from app.models.user import User

    user = db.get(User, principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return user


@router.post("/me/request-deletion", status_code=status.HTTP_202_ACCEPTED)
def request_deletion(
    reason: str | None = None,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    import uuid
    from datetime import datetime, timezone

    req = DataSubjectRequest(
        request_id=str(uuid.uuid4()),
        user_id=principal.user_id,
        request_type=RequestType.DELETE,
        reason=reason,
        status=RequestStatus.PENDING,
        requested_at=datetime.now(timezone.utc),
    )
    db.add(req)
    audit_service.log_event(
        db, audit_service.AuditEventType.DATA_DELETED, actor_user_id=principal.user_id,
        subject_user_id=principal.user_id, resource_type="data_subject_request",
        resource_id=req.request_id, metadata={"stage": "requested"},
    )
    db.commit()
    return {"detail": "deletion requested", "request_id": req.request_id}


@router.post("/me/request-anonymization", status_code=status.HTTP_202_ACCEPTED)
def request_anonymization(
    reason: str | None = None,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    import uuid
    from datetime import datetime, timezone

    req = DataSubjectRequest(
        request_id=str(uuid.uuid4()),
        user_id=principal.user_id,
        request_type=RequestType.ANONYMIZE,
        reason=reason,
        status=RequestStatus.PENDING,
        requested_at=datetime.now(timezone.utc),
    )
    db.add(req)
    audit_service.log_event(
        db, audit_service.AuditEventType.DATA_ANONYMIZED, actor_user_id=principal.user_id,
        subject_user_id=principal.user_id, resource_type="data_subject_request",
        resource_id=req.request_id, metadata={"stage": "requested"},
    )
    db.commit()
    return {"detail": "anonymization requested", "request_id": req.request_id}


@router.get("", response_model=list[UserPublic])
def list_users(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.models.user import User
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return rows
