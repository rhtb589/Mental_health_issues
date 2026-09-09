"""RBAC service: provider<->patient assignment scoping and access checks.

Enforces the role matrix:
  * Patient            -> only own records (ownership check)
  * Clinician          -> assigned patients only
  * Care Coordinator   -> assigned patients (view + limited edit)
  * Admin              -> full access (no scoping)
  * Researcher         -> aggregated / de-identified data only (never raw)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.security.authorization import Role
from app.models.assignment import Assignment


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def assign_provider(
    db: Session,
    patient_id: str,
    provider_id: str,
    provider_role: str,
    created_by: str | None,
) -> Assignment:
    if provider_role not in (Role.CLINICIAN, Role.CARE_COORDINATOR):
        raise ValueError("Only clinicians and care coordinators can be assigned patients")
    assignment = Assignment(
        assignment_id=str(uuid.uuid4()),
        patient_id=patient_id,
        provider_id=provider_id,
        provider_role=provider_role,
        created_at=_utcnow(),
        created_by=created_by,
        active=True,
    )
    db.add(assignment)
    db.flush()
    return assignment


def unassign_provider(db: Session, assignment_id: str) -> None:
    assignment = db.get(Assignment, assignment_id)
    if assignment:
        assignment.active = False
        db.flush()


def is_assigned(db: Session, provider_id: str, patient_id: str) -> bool:
    return (
        db.execute(
            select(Assignment).where(
                Assignment.provider_id == provider_id,
                Assignment.patient_id == patient_id,
                Assignment.active.is_(True),
            )
        )
        .scalars()
        .first()
        is not None
    )


def assigned_patient_ids(db: Session, provider_id: str) -> list[str]:
    rows = (
        db.execute(
            select(Assignment.patient_id).where(
                Assignment.provider_id == provider_id, Assignment.active.is_(True)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


def can_access_patient_data(
    db: Session, actor_id: str, actor_role: str, patient_id: str
) -> bool:
    """Authorize a privileged actor to access a specific patient's data."""
    role = Role(actor_role)
    if role == Role.ADMIN:
        return True
    if role in (Role.CLINICIAN, Role.CARE_COORDINATOR):
        return is_assigned(db, actor_id, patient_id)
    # Patients and researchers never get raw cross-patient access.
    return False
