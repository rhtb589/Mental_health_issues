"""Clinician / Care-Coordinator -> Patient assignments.

Requirement (RBAC): Clinician and Care Coordinator roles may only access
*assigned* patients. This table is the source of truth for that scoping. Admins
and Researchers are not subject to assignment scoping.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Uuid, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.security.authorization import Role


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    # Clinician or Care Coordinator user id.
    provider_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    provider_role: Mapped[str] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_by: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    patient: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[patient_id], back_populates="assignments_as_patient"
    )

    @property
    def is_coordinator(self) -> bool:
        return self.provider_role == Role.CARE_COORDINATOR
