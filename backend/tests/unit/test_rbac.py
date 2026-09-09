import uuid

from app.services import auth_service, rbac_service
from app.security.authorization import Role, ROLE_ACCESS_DESCRIPTION
from app.models.assignment import Assignment


def test_role_matrix_present():
    assert set(ROLE_ACCESS_DESCRIPTION) == {
        Role.PATIENT, Role.CLINICIAN, Role.CARE_COORDINATOR, Role.ADMIN, Role.RESEARCHER
    }


def test_admin_full_access(db):
    admin = auth_service.create_user(db, "a@x.com", "password123", role="admin")
    db.commit()
    assert rbac_service.can_access_patient_data(db, admin.user_id, "admin", "any-patient") is True


def test_clinician_scoped_by_assignment(db):
    patient = auth_service.create_user(db, "p@x.com", "password123", role="patient")
    clinician = auth_service.create_user(db, "c@x.com", "password123", role="clinician")
    db.commit()

    # Not assigned -> no access.
    assert rbac_service.can_access_patient_data(db, clinician.user_id, "clinician", patient.user_id) is False

    rbac_service.assign_provider(db, patient.user_id, clinician.user_id, "clinician", str(uuid.uuid4()))
    db.commit()
    assert rbac_service.can_access_patient_data(db, clinician.user_id, "clinician", patient.user_id) is True


def test_patient_cannot_access_others(db):
    patient = auth_service.create_user(db, "p@x.com", "password123", role="patient")
    db.commit()
    assert rbac_service.can_access_patient_data(db, patient.user_id, "patient", "someone-else") is False


def test_coordinator_assignment(db):
    patient = auth_service.create_user(db, "p@x.com", "password123", role="patient")
    coord = auth_service.create_user(db, "co@x.com", "password123", role="care_coordinator")
    db.commit()
    rbac_service.assign_provider(db, patient.user_id, coord.user_id, "care_coordinator", str(uuid.uuid4()))
    db.commit()
    assert rbac_service.can_access_patient_data(db, coord.user_id, "care_coordinator", patient.user_id) is True
