"""Screening assessments and responses.

Privacy design:
  * All screening answers and scores are *sensitive health data* and are stored
    encrypted at rest (see security/encryption.FieldEncryptor).
  * When a user prefers de-identified storage, responses/assessments are linked
    to a pseudonymous `subject_token` instead of `user_id` where possible.
  * `high_risk` flags cases (e.g. positive C-SSRS) that may require longer
    clinical retention (see retention service).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Uuid, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Assessment(Base):
    __tablename__ = "screening_assessments"

    assessment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    # Pseudonymous link used when stored de-identified (no user_id).
    subject_token: Mapped[str | None] = mapped_column(String(64), index=True)
    is_de_identified: Mapped[bool] = mapped_column(Boolean, default=False)

    instrument_id: Mapped[str] = mapped_column(String(50))
    instrument_version: Mapped[str | None] = mapped_column(String(20))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")

    # Sensitive health data -> encrypted blob (never plaintext in DB).
    encrypted_score: Mapped[str | None] = mapped_column(Text)
    encrypted_interpretation: Mapped[str | None] = mapped_column(Text)

    # Risk / retention.
    high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    encrypted_high_risk_detail: Mapped[str | None] = mapped_column(Text)
    retention_override_years: Mapped[int | None] = mapped_column(Integer)

    responses: Mapped[list["ScreeningResponse"]] = relationship(
        "ScreeningResponse", back_populates="assessment", cascade="all, delete-orphan"
    )
    user: Mapped["User | None"] = relationship("User", back_populates="assessments")


class ScreeningResponse(Base):
    __tablename__ = "screening_responses"

    response_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    assessment_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("screening_assessments.assessment_id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[str] = mapped_column(String(50))
    # Sensitive answer -> encrypted blob.
    encrypted_response_value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="responses")
