"""User model.

Privacy design:
  * Only necessary data is collected (basic profile; see requirement 1).
  * `prefers_de_identified` records the user's preference for de-identified
    storage of screening data where technically possible.
  * `data_residency_region` records where the record physically lives (India by
    default) and `data_transfer_disclosed` is set when a lawful cross-border
    transfer has been documented/disclosed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.security.authorization import Role


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Minimal profile (requirement: collect only necessary data).
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    age_group: Mapped[str | None] = mapped_column(String(20))  # child|adolescent|adult|elderly
    preferred_language: Mapped[str | None] = mapped_column(String(10))
    timezone: Mapped[str | None] = mapped_column(String(50))

    # Authentication / RBAC.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=Role.PATIENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Last activity used to drive retention (active + grace window).
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Privacy preferences / residency.
    prefers_de_identified: Mapped[bool] = mapped_column(Boolean, default=False)
    data_residency_region: Mapped[str] = mapped_column(String(10), default="in")
    data_transfer_disclosed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Set once the profile has been anonymized (identifiable data removed).
    anonymized: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships (lazy; not loaded unless accessed).
    assessments: Mapped[list["Assessment"]] = relationship(  # noqa: F821
        "Assessment", back_populates="user", cascade="all, delete-orphan"
    )
    consents: Mapped[list["ConsentRecord"]] = relationship(  # noqa: F821
        "ConsentRecord", back_populates="user", cascade="all, delete-orphan"
    )
    assignments_as_patient: Mapped[list["Assignment"]] = relationship(  # noqa: F821
        "Assignment",
        foreign_keys="Assignment.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    @property
    def is_patient(self) -> bool:
        return self.role == Role.PATIENT

    def effective_consent_status(self) -> str:
        """Derived 'given' if any active screening/storage consent exists."""
        for c in self.consents:
            if c.is_active and c.purpose in {"screening", "storage"}:
                return "given"
        return "withdrawn" if self.consents else "pending"
