"""Consent service.

Implements the consent lifecycle (requirement 2):
  * explicit consent for screening, storage, and sharing with a clinician
  * a SEPARATE optional consent for research use
  * withdrawal at any time -> triggers deletion / anonymization of affected data
  * every event records a timestamp + the consent text version
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.consent import (
    ConsentRecord,
    ConsentPurpose,
    ConsentStatus,
)
from app.models.retention_request import DataSubjectRequest, RequestType, RequestStatus
from app.services import audit_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def get_active_consents(db: Session, user_id: str) -> list[ConsentRecord]:
    return (
        db.execute(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id, ConsentRecord.is_active.is_(True)
            )
        )
        .scalars()
        .all()
    )


def has_consent(db: Session, user_id: str, purpose: str) -> bool:
    rec = (
        db.execute(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == purpose,
                ConsentRecord.status == ConsentStatus.GIVEN,
                ConsentRecord.is_active.is_(True),
            )
        )
        .scalars()
        .first()
    )
    return rec is not None


def _deactivate_existing(db: Session, user_id: str, purpose: str) -> None:
    existing = (
        db.execute(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == purpose,
                ConsentRecord.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    for e in existing:
        e.is_active = False


def record_consent(
    db: Session,
    user_id: str,
    purpose: str,
    *,
    recorded_by: str | None = None,
    consent_text: str | None = None,
    version: str | None = None,
    research: bool = False,
) -> ConsentRecord:
    """Record (or upgrade) a consent. Returns the new ConsentRecord."""
    if research:
        purpose = ConsentPurpose.RESEARCH
    if purpose not in (
        ConsentPurpose.SCREENING,
        ConsentPurpose.STORAGE,
        ConsentPurpose.SHARE_CLINICIAN,
        ConsentPurpose.RESEARCH,
    ):
        raise ValueError(f"Unknown consent purpose: {purpose}")

    _deactivate_existing(db, user_id, purpose)
    version = version or (
        settings.research_consent_text_version
        if purpose == ConsentPurpose.RESEARCH
        else settings.consent_text_version
    )
    record = ConsentRecord(
        consent_id=str(uuid.uuid4()),
        user_id=user_id,
        purpose=purpose,
        status=ConsentStatus.GIVEN,
        consent_text_version=version,
        consent_text_hash=_hash_text(consent_text) if consent_text else None,
        recorded_at=_utcnow(),
        effective_at=_utcnow(),
        is_active=True,
        recorded_by=recorded_by,
    )
    db.add(record)
    db.flush()
    audit_service.log_consent_event(
        db, audit_service.AuditEventType.CONSENT_GIVEN, user_id, purpose, recorded_by
    )
    return record


def withdraw_consent(
    db: Session,
    user_id: str,
    purpose: str,
    *,
    recorded_by: str | None = None,
    reason: str | None = None,
    cascade_delete: bool = True,
) -> ConsentRecord:
    """Withdraw a consent.

    If the withdrawn purpose is `screening` or `storage`, this triggers a
    data-subject request to delete or anonymize the affected data (per the
    requirement that withdrawal deletes or anonymizes data).
    """
    _deactivate_existing(db, user_id, purpose)
    record = ConsentRecord(
        consent_id=str(uuid.uuid4()),
        user_id=user_id,
        purpose=purpose,
        status=ConsentStatus.WITHDRAWN,
        consent_text_version=(
            settings.research_consent_text_version
            if purpose == ConsentPurpose.RESEARCH
            else settings.consent_text_version
        ),
        recorded_at=_utcnow(),
        effective_at=_utcnow(),
        withdrawn_at=_utcnow(),
        is_active=False,
        recorded_by=recorded_by,
    )
    db.add(record)
    db.flush()
    audit_service.log_consent_event(
        db, audit_service.AuditEventType.CONSENT_WITHDRAWN, user_id, purpose, recorded_by
    )

    if cascade_delete and purpose in (ConsentPurpose.SCREENING, ConsentPurpose.STORAGE):
        req = DataSubjectRequest(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            request_type=RequestType.ANONYMIZE,
            reason=reason or f"Consent withdrawn for '{purpose}'",
            status=RequestStatus.PENDING,
            requested_at=_utcnow(),
        )
        db.add(req)
        db.flush()

    return record
