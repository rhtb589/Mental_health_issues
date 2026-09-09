"""Audit logging service (tamper-proof hash chain).

Provides a single entry point for writing the audit events required by the
spec (login/logout, view/export sensitive data, assessment create/update/delete,
consent given/withdrawn, role changes, high-risk scores) and a verifier used by
admins and the cleanup worker to prove integrity.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.security.authorization import Role
from app.models.audit_log import (
    AuditLog,
    AuditEventType,
    canonical_payload,
    _sign,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def log_event(
    db: Session,
    event_type: str,
    actor_user_id: str | None = None,
    subject_user_id: str | None = None,
    *,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> AuditLog:
    """Append an audit event and chain it to the previous record."""
    occurred_at = occurred_at or _utcnow()

    # Fetch the most recent record's hash to chain from (by monotonic seq).
    last = (
        db.execute(
            select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)
        )
        .scalars()
        .first()
    )
    prev_hash = last.record_hash if last else "ROOT"
    next_seq = (db.execute(select(func.max(AuditLog.seq))).scalar() or 0) + 1

    record = AuditLog(
        event_id=str(uuid.uuid4()),
        seq=next_seq,
        event_type=event_type,
        occurred_at=occurred_at,
        actor_user_id=actor_user_id,
        subject_user_id=subject_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=json.dumps(metadata or {}, sort_keys=True, separators=(",", ":")),
        prev_hash=prev_hash,
    )
    record.record_hash = record.compute_hash()
    db.add(record)
    db.flush()
    return record


# Convenience wrappers for the spec's required events --------------------------------
def log_login(db: Session, user_id: str) -> None:
    log_event(db, AuditEventType.LOGIN, actor_user_id=user_id, subject_user_id=user_id)

def log_logout(db: Session, user_id: str) -> None:
    log_event(db, AuditEventType.LOGOUT, actor_user_id=user_id, subject_user_id=user_id)

def log_view_sensitive(db: Session, actor: str, subject: str, resource_type: str, resource_id: str) -> None:
    log_event(db, AuditEventType.VIEW_SENSITIVE, actor_user_id=actor, subject_user_id=subject,
              action="view", resource_type=resource_type, resource_id=resource_id)

def log_export_sensitive(db: Session, actor: str, subject: str, resource_type: str, resource_id: str) -> None:
    log_event(db, AuditEventType.EXPORT_SENSITIVE, actor_user_id=actor, subject_user_id=subject,
              action="export", resource_type=resource_type, resource_id=resource_id)

def log_assessment_create(db: Session, actor: str, subject: str, assessment_id: str) -> None:
    log_event(db, AuditEventType.ASSESSMENT_CREATE, actor_user_id=actor, subject_user_id=subject,
              action="create", resource_type="assessment", resource_id=assessment_id)

def log_assessment_update(db: Session, actor: str, subject: str, assessment_id: str) -> None:
    log_event(db, AuditEventType.ASSESSMENT_UPDATE, actor_user_id=actor, subject_user_id=subject,
              action="update", resource_type="assessment", resource_id=assessment_id)

def log_assessment_delete(db: Session, actor: str, subject: str, assessment_id: str) -> None:
    log_event(db, AuditEventType.ASSESSMENT_DELETE, actor_user_id=actor, subject_user_id=subject,
              action="delete", resource_type="assessment", resource_id=assessment_id)

def log_consent_event(db: Session, event_type: str, user_id: str, purpose: str, recorded_by: str | None) -> None:
    log_event(db, event_type, actor_user_id=recorded_by or user_id, subject_user_id=user_id,
              action=event_type, resource_type="consent", resource_id=purpose)

def log_role_change(db: Session, actor: str, subject: str, old_role: str, new_role: str) -> None:
    log_event(db, AuditEventType.ROLE_CHANGE, actor_user_id=actor, subject_user_id=subject,
              action="role_change", resource_type="user",
              metadata={"old_role": old_role, "new_role": new_role})

def log_high_risk_score(db: Session, actor: str, subject: str, assessment_id: str, detail: str) -> None:
    log_event(db, AuditEventType.HIGH_RISK_SCORE, actor_user_id=actor, subject_user_id=subject,
              action="generate", resource_type="assessment", resource_id=assessment_id,
              metadata={"detail": detail})


def verify_chain(db: Session) -> dict:
    """Recompute the hash chain and report integrity status.

    Returns a summary used by the admin integrity endpoint and periodic checks.
    """
    rows = (
        db.execute(select(AuditLog).order_by(AuditLog.seq.asc()))
        .scalars()
        .all()
    )
    prev_hash = "ROOT"
    broken_at = None
    for row in rows:
        if row.prev_hash != prev_hash:
            broken_at = row.event_id
            break
        if row.record_hash != row.compute_hash():
            broken_at = row.event_id
            break
        prev_hash = row.record_hash

    return {
        "total_records": len(rows),
        "chain_intact": broken_at is None,
        "first_broken_event_id": broken_at,
    }
