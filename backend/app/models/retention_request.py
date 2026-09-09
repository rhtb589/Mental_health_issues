"""Data-subject requests for deletion / anonymization (right to erasure).

Requirement (Retention & Consent): users can request deletion of their data at
any time, and withdrawing consent must delete or anonymize the affected data.
These requests are processed by the retention service / cleanup worker.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Uuid, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RequestType:
    DELETE = "delete"
    ANONYMIZE = "anonymize"


class RequestStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class DataSubjectRequest(Base):
    __tablename__ = "data_subject_requests"

    request_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), index=True)
    request_type: Mapped[str] = mapped_column(String(20))  # delete | anonymize
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=RequestStatus.PENDING)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_by: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
