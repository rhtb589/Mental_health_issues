from app.models.audit_log import AuditLog, AuditEventType
from app.models.retention_request import DataSubjectRequest, RequestStatus
from app.security.authentication import create_access_token
from sqlalchemy import select


def _register_and_login(client, email, password="password123", role="patient"):
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "role": role,
    })
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_register_login_audit(client, db):
    _register_and_login(client, "alice@example.com")
    events = db.execute(select(AuditLog.event_type)).scalars().all()
    assert AuditEventType.LOGIN in events


def test_assessment_requires_consent(client, db):
    token = _register_and_login(client, "bob@example.com")
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/assessments", json={"instrument_id": "PHQ9"}, headers=h)
    assert r.status_code == 403


def test_full_assessment_flow_audit_and_high_risk(client, db):
    token = _register_and_login(client, "carol@example.com")
    h = {"Authorization": f"Bearer {token}"}

    # Give required consents.
    assert client.post("/api/v1/consent/give", json={"purpose": "screening"}, headers=h).status_code == 201
    assert client.post("/api/v1/consent/give", json={"purpose": "storage"}, headers=h).status_code == 201

    # Start + respond + finalize high-risk.
    a = client.post("/api/v1/assessments", json={"instrument_id": "PHQ9"}, headers=h)
    assert a.status_code == 201
    aid = a.json()["assessment_id"]

    resp = client.post(f"/api/v1/assessments/{aid}/responses",
                       json={"question_id": "q1", "response_value": 3}, headers=h)
    assert resp.status_code == 201

    fin = client.post(f"/api/v1/assessments/{aid}/finalize",
                      json={"score": {"total": 23}, "interpretation": "severe",
                            "high_risk": True, "high_risk_detail": "PHQ9 severe"}, headers=h)
    assert fin.status_code == 200
    assert fin.json()["high_risk"] is True
    # Score must not be returned in plaintext to a non-owner viewer path; here owner sees it decrypted.
    assert fin.json()["score"] == {"total": 23}

    # High-risk score must be audited.
    events = db.execute(select(AuditLog.event_type)).scalars().all()
    assert AuditEventType.HIGH_RISK_SCORE in events
    assert AuditEventType.ASSESSMENT_CREATE in events
    # Viewing the assessment logs a sensitive-data view.
    client.get(f"/api/v1/assessments/{aid}", headers=h)
    view_events = db.execute(
        select(AuditLog).where(AuditLog.event_type == AuditEventType.VIEW_SENSITIVE)
    ).scalars().all()
    assert any(e.resource_id == aid for e in view_events)


def test_withdrawal_creates_erasure_request(client, db):
    token = _register_and_login(client, "dave@example.com")
    h = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/consent/give", json={"purpose": "storage"}, headers=h)
    r = client.post("/api/v1/consent/withdraw", json={"purpose": "storage"}, headers=h)
    assert r.status_code == 200
    req = db.execute(select(DataSubjectRequest).where(DataSubjectRequest.user_id.isnot(None))).scalars().first()
    assert req is not None and req.status == RequestStatus.PENDING


def test_researcher_sees_only_deidentified(db):
    # Seed an identifiable (non-deidentified) assessment.
    from app.services import auth_service, consent_service, assessment_service
    u = auth_service.create_user(db, "subj@example.com", "password123", role="patient")
    db.commit()
    consent_service.record_consent(db, u.user_id, "screening", recorded_by=u.user_id)
    consent_service.record_consent(db, u.user_id, "storage", recorded_by=u.user_id)
    db.commit()
    a = assessment_service.create_assessment(db, u, "PHQ9", "1.0")
    assessment_service.finalize_assessment(db, a, {"t": 5}, "mild", actor_id=u.user_id)
    db.commit()

    client = _client_with_role(db, "researcher@example.com", "researcher")
    r = client.get("/api/v1/research/aggregates/by-instrument")
    assert r.status_code == 200
    # No de-identified rows exist yet -> empty aggregate.
    assert r.json() == []


def _client_with_role(db, email, role):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    c = TestClient(app)
    c.post("/api/v1/auth/register", json={"email": email, "password": "password123", "role": role})
    login = c.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login.json()["access_token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_rbac_clinician_cannot_view_unassigned_patient(client, db):
    patient_token = _register_and_login(client, "pat@example.com")
    h = {"Authorization": f"Bearer {patient_token}"}
    client.post("/api/v1/consent/give", json={"purpose": "screening"}, headers=h)
    client.post("/api/v1/consent/give", json={"purpose": "storage"}, headers=h)
    aid = client.post("/api/v1/assessments", json={"instrument_id": "PHQ9"}, headers=h).json()["assessment_id"]

    clinician_client = _client_with_role(db, "doc@example.com", "clinician")
    r = clinician_client.get(f"/api/v1/assessments/{aid}")
    assert r.status_code == 404  # not assigned -> not found
