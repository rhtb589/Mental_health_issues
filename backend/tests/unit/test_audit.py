from app.services import audit_service
from app.models.audit_log import AuditLog, AuditEventType
from sqlalchemy import select


def test_chain_intact_after_appends(db):
    for i in range(3):
        audit_service.log_event(db, f"event_{i}", actor_user_id="a", subject_user_id="s")
    db.commit()
    res = audit_service.verify_chain(db)
    assert res["total_records"] == 3
    assert res["chain_intact"] is True


def test_tamper_detected_on_record_hash_change(db):
    for i in range(3):
        audit_service.log_event(db, f"event_{i}")
    db.commit()
    # Tamper with the middle record's content + stored hash.
    mid = db.execute(select(AuditLog).order_by(AuditLog.seq)).scalars().all()[1]
    mid.metadata_json = '{"x": 1}'
    mid.record_hash = "deadbeef"
    db.commit()
    res = audit_service.verify_chain(db)
    assert res["chain_intact"] is False
    assert res["first_broken_event_id"] == mid.event_id


def test_required_event_types_have_helpers(db):
    # Just ensure the helper functions emit the spec-required event types.
    audit_service.log_login(db, "u1")
    audit_service.log_logout(db, "u1")
    audit_service.log_view_sensitive(db, "u1", "u2", "assessment", "a1")
    audit_service.log_export_sensitive(db, "u1", "u2", "assessment", "a1")
    audit_service.log_assessment_create(db, "u1", "u2", "a1")
    audit_service.log_assessment_update(db, "u1", "u2", "a1")
    audit_service.log_assessment_delete(db, "u1", "u2", "a1")
    audit_service.log_consent_event(db, AuditEventType.CONSENT_GIVEN, "u2", "screening", "u1")
    audit_service.log_consent_event(db, AuditEventType.CONSENT_WITHDRAWN, "u2", "screening", "u1")
    audit_service.log_role_change(db, "admin", "u2", "patient", "clinician")
    audit_service.log_high_risk_score(db, "u1", "u2", "a1", "C-SSRS positive")
    db.commit()
    types = set(db.execute(select(AuditLog.event_type)).scalars().all())
    required = {
        AuditEventType.LOGIN, AuditEventType.LOGOUT, AuditEventType.VIEW_SENSITIVE,
        AuditEventType.EXPORT_SENSITIVE, AuditEventType.ASSESSMENT_CREATE,
        AuditEventType.ASSESSMENT_UPDATE, AuditEventType.ASSESSMENT_DELETE,
        AuditEventType.CONSENT_GIVEN, AuditEventType.CONSENT_WITHDRAWN,
        AuditEventType.ROLE_CHANGE, AuditEventType.HIGH_RISK_SCORE,
    }
    assert required.issubset(types)
