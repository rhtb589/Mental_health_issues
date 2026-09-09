"""Role-Based Access Control (RBAC) definitions.

Requirement (RBAC):
  User/Patient   -> own data and scores only
  Clinician      -> assigned patients only
  Care Coordinator-> assigned patients (view + limited edit)
  Admin          -> full system access
  Researcher     -> anonymized / aggregated data only

Roles are stored on the User model. Patient-scoped roles (clinician,
coordinator) are additionally constrained by explicit assignments (see
models/assignment.py and services/rbac_service.py).
"""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    PATIENT = "patient"          # aka "User"
    CLINICIAN = "clinician"
    CARE_COORDINATOR = "care_coordinator"
    ADMIN = "admin"
    RESEARCHER = "researcher"


# Human-readable access summaries (used in disclosures / admin UI).
ROLE_ACCESS_DESCRIPTION: dict[Role, str] = {
    Role.PATIENT: "Own data and scores only",
    Role.CLINICIAN: "Assigned patients only",
    Role.CARE_COORDINATOR: "Assigned patients (view + limited edit)",
    Role.ADMIN: "Full system access",
    Role.RESEARCHER: "Anonymized / aggregated data only",
}


def is_privileged_role(role: str) -> bool:
    """True for roles that operate over other people's data (always scoped)."""
    return role in {Role.CLINICIAN, Role.CARE_COORDINATOR, Role.ADMIN, Role.RESEARCHER}
