"""Assessment service.

Encapsulates creation, scoring and persistence of screening assessments while
enforcing:
  * consent must be granted before storing (Privacy/Consent)
  * answers and scores are encrypted at rest (Privacy)
  * de-identified storage when the user prefers it (Privacy)
  * high-risk score generation is audit-logged (Audit)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.security.encryption import FieldEncryptor
from app.models.assessment import Assessment, ScreeningResponse
from app.models.user import User
from app.services import audit_service, consent_service, rbac_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_assessment(
    db: Session,
    user: User,
    instrument_id: str,
    instrument_version: str | None,
    *,
    actor_id: str | None = None,
) -> Assessment:
    """Create an assessment. Starting a screening requires explicit consent."""
    if not consent_service.has_consent(db, user.user_id, "screening"):
        raise PermissionError("Screening consent required before starting a screening")
    # When the user prefers de-identification, we still create a user-linked
    # assessment but mark it de-identified and use a subject token going forward.
    assessment = Assessment(
        assessment_id=str(uuid.uuid4()),
        user_id=user.user_id if not user.prefers_de_identified else None,
        subject_token=None if not user.prefers_de_identified else uuid.uuid4().hex,
        is_de_identified=user.prefers_de_identified,
        instrument_id=instrument_id,
        instrument_version=instrument_version,
        started_at=_utcnow(),
        status="in_progress",
    )
    db.add(assessment)
    db.flush()
    audit_service.log_assessment_create(
        db, actor=actor_id or user.user_id, subject=user.user_id,
        assessment_id=assessment.assessment_id,
    )
    return assessment


def add_response(
    db: Session,
    assessment: Assessment,
    question_id: str,
    response_value: Any,
    *,
    encryptor: FieldEncryptor | None = None,
) -> ScreeningResponse:
    encryptor = encryptor or FieldEncryptor()
    response = ScreeningResponse(
        response_id=str(uuid.uuid4()),
        assessment_id=assessment.assessment_id,
        question_id=question_id,
        encrypted_response_value=encryptor.encrypt(response_value),
    )
    db.add(response)
    db.flush()
    return response


def finalize_assessment(
    db: Session,
    assessment: Assessment,
    score: Any,
    interpretation: str,
    *,
    high_risk: bool = False,
    high_risk_detail: str | None = None,
    actor_id: str | None = None,
    encryptor: FieldEncryptor | None = None,
) -> Assessment:
    encryptor = encryptor or FieldEncryptor()
    if not consent_service.has_consent(db, assessment.user_id or "", "storage") and not assessment.is_de_identified:
        raise PermissionError("Storage consent required before persisting results")
    assessment.encrypted_score = encryptor.encrypt(score)
    assessment.encrypted_interpretation = encryptor.encrypt(interpretation)
    assessment.completed_at = _utcnow()
    assessment.status = "completed"
    assessment.high_risk = high_risk
    if high_risk_detail:
        assessment.encrypted_high_risk_detail = encryptor.encrypt(high_risk_detail)
    db.flush()
    audit_service.log_assessment_update(
        db, actor=actor_id or (assessment.user_id or "system"),
        subject=assessment.user_id, assessment_id=assessment.assessment_id,
    )
    if high_risk:
        audit_service.log_high_risk_score(
            db, actor=actor_id or (assessment.user_id or "system"),
            subject=assessment.user_id, assessment_id=assessment.assessment_id,
            detail=high_risk_detail or "High-risk screening result generated",
        )
    return assessment


def get_assessment_for_principal(
    db: Session, principal, assessment_id: str
) -> Assessment | None:
    """Return the assessment only if the principal is authorized to view it."""
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        return None
    if principal.role == "patient":
        if assessment.user_id != principal.user_id:
            return None
        return assessment
    if principal.is_admin:
        return assessment
    if assessment.user_id and rbac_service.can_access_patient_data(
        db, principal.user_id, principal.role, assessment.user_id
    ):
        return assessment
    return None
