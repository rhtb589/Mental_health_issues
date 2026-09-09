"""Consent endpoints.

Requirement (Consent): explicit, versioned, timestamped consent for screening,
storage, clinician sharing and (separately) research; withdrawal at any time
which triggers deletion / anonymization of affected data.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.consent import ConsentGive, ConsentOut, ConsentWithdraw
from app.security.permissions import get_current_principal, Principal
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("", response_model=list[ConsentOut])
def list_consents(principal: Principal = Depends(get_current_principal), db: Session = Depends(get_db)):
    recs = consent_service.get_active_consents(db, principal.user_id)
    return [_to_out(r) for r in recs]


@router.post("/give", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
def give_consent(
    payload: ConsentGive,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    try:
        rec = consent_service.record_consent(
            db,
            principal.user_id,
            payload.purpose,
            recorded_by=principal.user_id,
            consent_text=payload.consent_text,
            version=payload.version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.commit()
    db.refresh(rec)
    return _to_out(rec)


@router.post("/withdraw", response_model=ConsentOut)
def withdraw_consent(
    payload: ConsentWithdraw,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    rec = consent_service.withdraw_consent(
        db,
        principal.user_id,
        payload.purpose,
        recorded_by=principal.user_id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(rec)
    return _to_out(rec)


def _to_out(r):
    return ConsentOut(
        consent_id=r.consent_id,
        purpose=r.purpose,
        status=r.status,
        consent_text_version=r.consent_text_version,
        recorded_at=r.recorded_at.isoformat() if r.recorded_at else "",
        is_active=r.is_active,
        withdrawn_at=r.withdrawn_at.isoformat() if r.withdrawn_at else None,
    )
