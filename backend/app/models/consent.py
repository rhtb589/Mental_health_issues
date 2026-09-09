"""Consent records.

Requirement (Consent):
  * Clear consent required before screening, storing results, sharing with a
    clinician; a *separate* optional consent governs research use.
  * Users can withdraw consent any time -> data deleted or anonymized.
  * Every consent event is recorded with a timestamp and the version of the
    consent text that was presented.

A ConsentRecord is append-only: withdrawing creates a new record (status=
'withdrawn') so we keep a full, auditable history. Only the latest record per
(purpose) reflects the current state; `is_active` is a convenience flag.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Uuid, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConsentPurpose:
    SCREENING = "screening"        # start a screening
    STORAGE = "storage"            # store results
    SHARE_CLINICIAN = "share_clinician"  # share with an assigned clinician
    RESEARCH = "research"          # optional, separate


class ConsentStatus:
    GIVEN = "given"
    WITHDRAWN = "withdrawn"


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    consent_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(20), default=ConsentStatus.GIVEN)

    # Version of the consent text presented (requirement: record version).
    consent_text_version: Mapped[str] = mapped_column(String(20))
    # Optional free-form snapshot / hash of the exact text shown to the user.
    consent_text_hash: Mapped[str | None] = mapped_column(String(64))

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Convenience flag for "currently in force".
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Denormalised actor for audit (who recorded/withdrew).
    recorded_by: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))

    user: Mapped["User"] = relationship("User", back_populates="consents")  # noqa: F821
