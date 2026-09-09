from datetime import datetime, timezone

from app.models.user import User
from app.models.consent import ConsentRecord, ConsentPurpose, ConsentStatus
from app.models.retention_request import DataSubjectRequest, RequestType, RequestStatus
from app.services import auth_service, consent_service, assessment_service


def _make_user(db):
    u = auth_service.create_user(db, "p@example.com", "password123", role="patient")
    db.commit()
    return u


def test_screening_blocked_without_consent(db):
    u = _make_user(db)
    try:
        assessment_service.create_assessment(db, u, "PHQ9", "1.0")
        assert False, "should require screening consent"
    except PermissionError:
        pass


def test_separate_research_consent(db):
    u = _make_user(db)
    consent_service.record_consent(db, u.user_id, ConsentPurpose.SCREENING, recorded_by=u.user_id)
    consent_service.record_consent(db, u.user_id, ConsentPurpose.RESEARCH, recorded_by=u.user_id)
    db.commit()
    assert consent_service.has_consent(db, u.user_id, ConsentPurpose.SCREENING)
    assert consent_service.has_consent(db, u.user_id, ConsentPurpose.RESEARCH)


def test_consent_records_version_and_timestamp(db):
    u = _make_user(db)
    rec = consent_service.record_consent(
        db, u.user_id, ConsentPurpose.SCREENING, recorded_by=u.user_id,
        consent_text="I consent to screening", version="2024-08-01",
    )
    db.commit()
    assert rec.consent_text_version == "2024-08-01"
    assert rec.recorded_at is not None
    assert rec.status == ConsentStatus.GIVEN
    assert rec.consent_text_hash is not None


def test_withdrawal_deactivates_and_creates_request(db):
    u = _make_user(db)
    consent_service.record_consent(db, u.user_id, ConsentPurpose.STORAGE, recorded_by=u.user_id)
    db.commit()
    assert consent_service.has_consent(db, u.user_id, ConsentPurpose.STORAGE)

    consent_service.withdraw_consent(db, u.user_id, ConsentPurpose.STORAGE, recorded_by=u.user_id)
    db.commit()

    assert not consent_service.has_consent(db, u.user_id, ConsentPurpose.STORAGE)
    # Withdrawing storage consent must cascade to a data-subject request.
    req = db.execute(
        __import__("sqlalchemy").select(DataSubjectRequest).where(
            DataSubjectRequest.user_id == u.user_id
        )
    ).scalars().first()
    assert req is not None
    assert req.request_type == RequestType.ANONYMIZE


def test_history_preserved_after_withdrawal(db):
    u = _make_user(db)
    consent_service.record_consent(db, u.user_id, ConsentPurpose.SCREENING, recorded_by=u.user_id)
    consent_service.withdraw_consent(db, u.user_id, ConsentPurpose.SCREENING, recorded_by=u.user_id)
    db.commit()
    recs = db.execute(
        __import__("sqlalchemy").select(ConsentRecord).where(ConsentRecord.user_id == u.user_id)
    ).scalars().all()
    assert len(recs) == 2  # given + withdrawn (append-only)
