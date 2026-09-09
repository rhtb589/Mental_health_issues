"""Assessment endpoints.

Sensitive answers and scores are encrypted at rest, consent-gated, and access
is restricted by RBAC. Viewing/exporting sensitive data is audit-logged.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.encryption import FieldEncryptor
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentFinalize,
    AssessmentOut,
    ResponseAdd,
)
from app.security.permissions import get_current_principal, Principal
from app.services import assessment_service, rbac_service, audit_service

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _load(db, principal, assessment_id):
    assessment = assessment_service.get_assessment_for_principal(db, principal, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return assessment


@router.post("", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def start_screening(
    payload: AssessmentCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    try:
        assessment = assessment_service.create_assessment(
            db, principal_user(principal, db), payload.instrument_id, payload.instrument_version,
            actor_id=principal.user_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    db.commit()
    db.refresh(assessment)
    return _to_out(assessment, principal, db)


@router.post("/{assessment_id}/responses", status_code=status.HTTP_201_CREATED)
def add_response(
    assessment_id: str,
    payload: ResponseAdd,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    assessment = _load(db, principal, assessment_id)
    assessment_service.add_response(db, assessment, payload.question_id, payload.response_value)
    db.commit()
    return {"detail": "ok"}


@router.post("/{assessment_id}/finalize", response_model=AssessmentOut)
def finalize(
    assessment_id: str,
    payload: AssessmentFinalize,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    assessment = _load(db, principal, assessment_id)
    try:
        assessment = assessment_service.finalize_assessment(
            db, assessment, payload.score, payload.interpretation,
            high_risk=payload.high_risk, high_risk_detail=payload.high_risk_detail,
            actor_id=principal.user_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    db.commit()
    db.refresh(assessment)
    return _to_out(assessment, principal, db)


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(
    assessment_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    assessment = _load(db, principal, assessment_id)
    # Audit: viewing sensitive data.
    audit_service.log_view_sensitive(
        db, actor=principal.user_id, subject=assessment.user_id or "deidentified",
        resource_type="assessment", resource_id=assessment.assessment_id,
    )
    db.commit()
    return _to_out(assessment, principal, db)


@router.get("", response_model=list[AssessmentOut])
def list_assessments(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    from app.models.assessment import Assessment
    from sqlalchemy import select

    if principal.role == "patient":
        rows = db.execute(
            select(Assessment).where(Assessment.user_id == principal.user_id)
        ).scalars().all()
    elif principal.is_admin:
        rows = db.execute(select(Assessment)).scalars().all()
    else:
        ids = rbac_service.assigned_patient_ids(db, principal.user_id)
        rows = db.execute(
            select(Assessment).where(Assessment.user_id.in_(ids))
        ).scalars().all() if ids else []
    return [_to_out(a, principal, db) for a in rows]


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    assessment = _load(db, principal, assessment_id)
    audit_service.log_event(
        db, event_type="ASSESSMENT_DELETE",
        actor_user_id=principal.user_id, subject_user_id=assessment.user_id or "deidentified",
        action="delete", resource_type="assessment", resource_id=assessment.assessment_id,
    )
    db.delete(assessment)
    db.commit()


def principal_user(principal, db):
    from app.models.user import User
    return db.get(User, principal.user_id)


def _to_out(assessment, principal, db, encryptor: FieldEncryptor | None = None):
    encryptor = encryptor or FieldEncryptor()
    is_owner = assessment.user_id == principal.user_id
    can_decrypt = is_owner or principal.is_admin or (
        assessment.user_id
        and rbac_service.can_access_patient_data(db, principal.user_id, principal.role, assessment.user_id)
    )
    score = interpretation = high_risk_detail = None
    if can_decrypt and assessment.encrypted_score:
        score = encryptor.decrypt(assessment.encrypted_score)
        interpretation = encryptor.decrypt(assessment.encrypted_interpretation) \
            if assessment.encrypted_interpretation else None
        high_risk_detail = encryptor.decrypt(assessment.encrypted_high_risk_detail) \
            if assessment.encrypted_high_risk_detail else None
    return AssessmentOut(
        assessment_id=assessment.assessment_id,
        instrument_id=assessment.instrument_id,
        instrument_version=assessment.instrument_version,
        status=assessment.status,
        high_risk=assessment.high_risk,
        high_risk_detail=high_risk_detail,
        is_de_identified=assessment.is_de_identified,
        started_at=assessment.started_at.isoformat() if assessment.started_at else "",
        completed_at=assessment.completed_at.isoformat() if assessment.completed_at else None,
        score=score,
        interpretation=interpretation,
    )
