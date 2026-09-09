"""Data retention service.

Requirement (Retention):
  * Identifiable data kept only while the user is active + max 3-5 years.
  * After the retention period -> automatically anonymize or delete.
  * High-risk cases (e.g. positive C-SSRS) may follow longer clinical retention.
  * Users may request deletion of their data at any time.

`anonymize` removes direct identifiers but keeps de-identified screening data
linked to a pseudonymous token (for longitudinal / research use). `delete`
removes the data subject entirely (cascading to assessments & responses).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.security.encryption import random_subject_token
from app.models.assessment import Assessment
from app.models.retention_request import (
    DataSubjectRequest,
    RequestStatus,
    RequestType,
)
from app.models.user import User
from app.services import audit_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalize a datetime to timezone-aware UTC (SQLite returns naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_user_expired(db: Session, user: User, now: datetime | None = None) -> bool:
    """A user's identifiable data is expired when either:
      * they have been inactive longer than the grace window, OR
      * their account exceeds the hard retention cap.
    """
    now = _as_utc(now or _utcnow())
    la = _as_utc(user.last_active_at)
    ca = _as_utc(user.created_at)
    grace_cutoff = now - timedelta(days=settings.inactive_grace_days)
    hard_cutoff = now - timedelta(days=365 * settings.identifiable_retention_years)
    inactive_too_long = la is not None and la < grace_cutoff
    too_old = ca is not None and ca < hard_cutoff
    return (inactive_too_long or too_old) and not user.anonymized


def collect_expired_users(db: Session, now: datetime | None = None) -> list[User]:
    now = now or _utcnow()
    users = db.execute(select(User).where(User.anonymized.is_(False))).scalars().all()
    return [u for u in users if is_user_expired(db, u, now)]


def is_high_risk_assessment_expired(db: Session, assessment: Assessment, now: datetime | None = None) -> bool:
    if not assessment.high_risk or not assessment.completed_at:
        return False
    now = _as_utc(now or _utcnow())
    completed = _as_utc(assessment.completed_at)
    years = assessment.retention_override_years or settings.high_risk_retention_years
    return completed < now - timedelta(days=365 * years)


def anonymize_user(db: Session, user_id: str, *, actor: str = "system") -> None:
    """Strip direct identifiers; keep de-identified screening data."""
    user = db.get(User, user_id)
    if user is None or user.anonymized:
        return
    token = random_subject_token()
    for assessment in user.assessments:
        assessment.user_id = None
        assessment.subject_token = token
        assessment.is_de_identified = True
    user.email = None
    user.password_hash = ""  # cannot authenticate after anonymization
    user.date_of_birth = None
    user.age_group = None
    user.preferred_language = None
    user.timezone = None
    user.is_active = False
    user.anonymized = True
    db.flush()
    audit_service.log_event(
        db, audit_service.AuditEventType.DATA_ANONYMIZED, actor_user_id=actor,
        subject_user_id=user_id, resource_type="user", resource_id=user_id,
    )


def delete_user_data(db: Session, user_id: str, *, actor: str = "system") -> None:
    """Hard-delete the data subject and all directly linked identifiable data."""
    user = db.get(User, user_id)
    if user is None:
        return
    # Cascade removes assessments/responses/consents/assignments; audit logs are
    # intentionally preserved (they only store opaque ids + hashes).
    db.delete(user)
    db.flush()
    audit_service.log_event(
        db, audit_service.AuditEventType.DATA_DELETED, actor_user_id=actor,
        subject_user_id=user_id, resource_type="user", resource_id=user_id,
    )


def process_data_subject_request(db: Session, request: DataSubjectRequest) -> None:
    request.status = RequestStatus.PROCESSING
    db.flush()
    try:
        if request.request_type == RequestType.DELETE:
            delete_user_data(db, request.user_id, actor=request.processed_by or "system")
        else:
            anonymize_user(db, request.user_id, actor=request.processed_by or "system")
        request.status = RequestStatus.DONE
        request.processed_at = _utcnow()
        db.flush()
    except Exception:
        request.status = RequestStatus.FAILED
        db.flush()
        raise


def process_all_pending_requests(db: Session) -> int:
    pending = (
        db.execute(
            select(DataSubjectRequest).where(DataSubjectRequest.status == RequestStatus.PENDING)
        )
        .scalars()
        .all()
    )
    count = 0
    for req in pending:
        process_data_subject_request(db, req)
        count += 1
    return count


def run_retention_sweep(db: Session, now: datetime | None = None) -> dict:
    """Scheduled job: anonymize expired users and process pending requests."""
    now = now or _utcnow()
    expired = collect_expired_users(db, now)
    for user in expired:
        anonymize_user(db, user.user_id)
    # High-risk assessments that have exceeded their clinical retention window.
    high_risk = (
        db.execute(select(Assessment).where(Assessment.high_risk.is_(True))).scalars().all()
    )
    anonymized_high_risk = 0
    for a in high_risk:
        if is_high_risk_assessment_expired(db, a, now):
            a.user_id = None
            a.subject_token = a.subject_token or random_subject_token()
            a.is_de_identified = True
            anonymized_high_risk += 1
    processed = process_all_pending_requests(db)
    db.flush()
    return {
        "anonymized_users": len(expired),
        "anonymized_high_risk_assessments": anonymized_high_risk,
        "processed_subject_requests": processed,
    }
