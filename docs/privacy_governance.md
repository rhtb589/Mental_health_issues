# Privacy, Consent, Retention, RBAC & Audit — Implementation

This document maps each requirement in the brief to the code that implements it.

| Area | Where |
|------|-------|
| Privacy | `app/security/encryption.py`, `app/models/assessment.py`, `app/core/config.py` |
| Consent | `app/services/consent_service.py`, `app/api/consent.py`, `app/models/consent.py` |
| Retention | `app/services/retention_service.py`, `app/workers/cleanup.py`, `app/api/users.py` |
| RBAC | `app/security/authorization.py`, `app/security/permissions.py`, `app/services/rbac_service.py` |
| Audit | `app/models/audit_log.py`, `app/services/audit_service.py`, `app/api/admin.py` |

---

## 1. Privacy
- **Minimal data collection**: `app/models/user.py` captures only a basic profile
  (DOB, age group, language, timezone); no surplus PII.
- **Sensitive health data**: all screening answers (`screening_responses.encrypted_response_value`)
  and scores/interpretations (`screening_assessments.encrypted_score`,
  `encrypted_interpretation`) are encrypted at rest via
  `app/security/encryption.py` (`FieldEncryptor`, Fernet/AES+HMAC). Decryption only
  happens for authorized viewers in `app/api/assessments.py::_to_out`.
- **De-identified storage**: users may set `prefers_de_identified`; assessments are
  then linked to a `subject_token` instead of `user_id`
  (`app/services/assessment_service.py::create_assessment`).
- **No third-party sharing**: there is no external/third-party data egress path; any
  sharing requires explicit `share_clinician` consent and an assignment (RBAC).
- **Data residency**: `data_residency_region` defaults to `in` (India);
  `data_transfer_disclosed` must be set explicitly if a cross-border transfer is ever
  introduced (`app/core/config.py`, `app/models/user.py`).

## 2. Consent
- Distinct consents for **screening**, **storage**, **share_clinician**, and a
  *separate* optional **research** consent (`app/models/consent.py`).
- Consent is **checked before** any action:
  - starting a screening → `screening` consent
  - persisting results → `storage` consent
  - clinician access → `share_clinician` + assignment
- Every consent event records a **timestamp** (`recorded_at`) and the **version** of
  the consent text (`consent_text_version`) plus an optional text hash
  (`consent_text_hash`).
- **Withdrawal at any time** triggers a data-subject request to **delete or
  anonymize** affected data (`app/services/consent_service.py::withdraw_consent`).
- Records are append-only (new `withdrawn` row) so the full history is preserved.

## 3. Data Retention
- Identifiable data is kept only while the user is active plus a maximum window
  (`MHC_IDENTIFIABLE_RETENTION_YEARS`, default 5 within the 3–5 range) and an
  inactivity grace (`MHC_INACTIVE_GRACE_DAYS`).
- After expiry the **retention sweep anonymizes** (strips identifiers, keeps
  de-identified screening data) or **deletes** data
  (`app/services/retention_service.py::run_retention_sweep`, `workers/cleanup.py`).
- **High-risk cases** (e.g. positive C-SSRS, `high_risk=True`) follow a longer
  clinical retention (`MHC_HIGH_RISK_RETENTION_YEARS`, default 7) via
  `retention_override_years`.
- Users may **request deletion/anonymization any time** via
  `POST /api/v1/users/me/request-deletion` and `/request-anonymization`.

## 4. Role-Based Access Control (RBAC)
Roles (`app/security/authorization.py::Role`):

| Role | Access |
|------|--------|
| patient (User) | own data/scores only |
| clinician | assigned patients only |
| care_coordinator | assigned patients (view + limited edit) |
| admin | full system access |
| researcher | anonymized / aggregated data only |

- Enforcement: `app/security/permissions.py` (`get_current_principal`, `require_role`,
  `require_admin`) and `app/services/rbac_service.py::can_access_patient_data`
  (scoped by `assignments` table).
- Researchers are deliberately limited to aggregate endpoints
  (`app/api/research.py`) that never return identifiable records.

## 5. Audit Logging
- Tamper-proof via a **hash chain** (`app/models/audit_log.py`): each record stores
  `prev_hash` (hash of previous record) and `record_hash` (HMAC over its canonical
  payload using `MHC_JWT_SECRET`). Any tampering breaks the chain, verifiable via
  `verify_chain()` and `GET /api/v1/admin/audit/integrity`.
- Logged events (all required): login, logout, viewing/exporting sensitive data,
  creating/updating/deleting assessments, consent given/withdrawn, role changes,
  generation of high-risk scores (`app/services/audit_service.py`).
- Retained for at least 2–3 years (`MHC_AUDIT_LOG_RETENTION_YEARS`); audit rows
  reference only opaque ids (they survive user deletion/anonymization).
