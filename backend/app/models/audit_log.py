"""Tamper-proof audit log.

Requirement (Audit Logging):
  * Events: login/logout, view/export of sensitive data, create/update/delete of
    assessments, consent given/withdrawn, role changes, generation of high-risk
    scores.
  * Logs must be tamper-proof and retained for at least 2-3 years.

Tamper-evidence is achieved with a *hash chain*: each record stores the hash of
the previous record plus an HMAC over its own canonical payload, keyed by a
server-side secret. Any modification, deletion or reordering of records breaks
the chain, which is verifiable via `verify_chain()` / the maintenance endpoint.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, Uuid, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEventType:
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW_SENSITIVE = "view_sensitive"
    EXPORT_SENSITIVE = "export_sensitive"
    ASSESSMENT_CREATE = "assessment_create"
    ASSESSMENT_UPDATE = "assessment_update"
    ASSESSMENT_DELETE = "assessment_delete"
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    ROLE_CHANGE = "role_change"
    HIGH_RISK_SCORE = "high_risk_score"
    DATA_DELETED = "data_deleted"
    DATA_ANONYMIZED = "data_anonymized"


def _sign(canonical: str, prev_hash: str) -> str:
    key = settings.jwt_secret.encode()
    return hmac.new(key, (prev_hash + "|" + canonical).encode(), hashlib.sha256).hexdigest()


def _norm_ts(dt: datetime) -> str:
    """Normalize a datetime to a tz-naive UTC ISO string for stable hashing
    across databases (Postgres TIMESTAMPTZ vs SQLite naive round-tripping)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat()


def canonical_payload(event_type: str, actor_id: str | None, subject_id: str | None,
                      action: str, resource_type: str | None, resource_id: str | None,
                      metadata: dict[str, Any], occurred_at: datetime) -> str:
    return json.dumps(
        {
            "event_type": event_type,
            "actor_id": actor_id,
            "subject_id": subject_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "occurred_at": _norm_ts(occurred_at),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    event_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    # Monotonic insertion order guaranteeing a deterministic hash-chain order
    # even when multiple events share the same occurred_at timestamp.
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    # Who performed the action (may be 'system' for automated events, or an
    # opaque pseudonymous token for de-identified data).
    actor_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    # Whose data was affected (the data subject; may be a pseudonymous token).
    subject_user_id: Mapped[str | None] = mapped_column(String(64), index=True)

    action: Mapped[str | None] = mapped_column(String(40))
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[str | None] = mapped_column(String(120))

    metadata_json: Mapped[str | None] = mapped_column(Text)

    # Hash chain linkage.
    prev_hash: Mapped[str] = mapped_column(String(64), default="ROOT")
    record_hash: Mapped[str] = mapped_column(String(64), index=True)

    def compute_hash(self) -> str:
        canonical = canonical_payload(
            self.event_type,
            self.actor_user_id,
            self.subject_user_id,
            self.action or "",
            self.resource_type,
            self.resource_id,
            self._metadata_obj(),
            self.occurred_at,
        )
        return _sign(canonical, self.prev_hash)

    def _metadata_obj(self) -> dict[str, Any]:
        if not self.metadata_json:
            return {}
        return json.loads(self.metadata_json)
