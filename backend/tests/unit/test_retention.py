from datetime import datetime, timezone, timedelta

from app.services import auth_service, consent_service, assessment_service, retention_service
from app.models.assessment import Assessment
from app.models.retention_request import DataSubjectRequest, RequestType, RequestStatus
from sqlalchemy import select


def _seed_assessment(db, user):
    consent_service.record_consent(db, user.user_id, "screening", recorded_by=user.user_id)
    consent_service.record_consent(db, user.user_id, "storage", recorded_by=user.user_id)
    db.commit()
    a = assessment_service.create_assessment(db, user, "PHQ9", "1.0")
    assessment_service.finalize_assessment(db, a, {"t": 10}, "moderate", actor_id=user.user_id)
    db.commit()
    return a


def test_anonymize_strips_identifiers_and_keeps_data(db):
    u = auth_service.create_user(db, "p@example.com", "password123", role="patient")
    db.commit()
    a = _seed_assessment(db, u)

    retention_service.anonymize_user(db, u.user_id)
    db.commit()
    db.expire_all()

    reloaded = db.get(type(u), u.user_id)
    assert reloaded.email is None
    assert reloaded.anonymized is True
    assert reloaded.is_active is False

    a2 = db.get(Assessment, a.assessment_id)
    assert a2.user_id is None
    assert a2.is_de_identified is True
    assert a2.subject_token is not None


def test_delete_removes_user(db):
    u = auth_service.create_user(db, "p@example.com", "password123", role="patient")
    db.commit()
    a = _seed_assessment(db, u)
    retention_service.delete_user_data(db, u.user_id)
    db.commit()
    assert db.get(type(u), u.user_id) is None
    # Assessments cascade-deleted.
    assert db.get(Assessment, a.assessment_id) is None


def test_user_expiry_logic(db):
    old = datetime(2015, 1, 1, tzinfo=timezone.utc)
    u = auth_service.create_user(db, "old@example.com", "password123", role="patient")
    u.created_at = old
    u.last_active_at = old
    db.commit()
    assert retention_service.is_user_expired(db, u) is True

    fresh = auth_service.create_user(db, "new@example.com", "password123", role="patient")
    fresh.last_active_at = datetime.now(timezone.utc)
    db.commit()
    assert retention_service.is_user_expired(db, fresh) is False


def test_high_risk_extension(db):
    u = auth_service.create_user(db, "hr@example.com", "password123", role="patient")
    db.commit()
    a = _seed_assessment(db, u)
    a.high_risk = True
    a.completed_at = datetime(2015, 1, 1, tzinfo=timezone.utc)
    db.commit()
    # Default high-risk retention is 7 years, so 2015 is expired.
    assert retention_service.is_high_risk_assessment_expired(db, a) is True

    recent = datetime.now(timezone.utc) - timedelta(days=365)
    a.completed_at = recent
    db.commit()
    assert retention_service.is_high_risk_assessment_expired(db, a) is False


def test_sweep_processes_pending_requests(db):
    u = auth_service.create_user(db, "req@example.com", "password123", role="patient")
    db.commit()
    _seed_assessment(db, u)
    req = DataSubjectRequest(
        request_id=__import__("uuid").uuid4().hex,
        user_id=u.user_id, request_type=RequestType.DELETE,
        status=RequestStatus.PENDING, requested_at=datetime.now(timezone.utc),
    )
    db.add(req)
    db.commit()

    summary = retention_service.run_retention_sweep(db)
    db.commit()
    assert summary["processed_subject_requests"] == 1
    assert db.get(type(u), u.user_id) is None
