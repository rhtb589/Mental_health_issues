-- PostgreSQL schema for the Mental Health Screening App
-- Enforces Privacy, Consent, Retention, RBAC & Audit requirements.
-- Tables are aligned with backend/app/models/*.py

CREATE TABLE IF NOT EXISTS users (
    user_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Minimal profile (Privacy: collect only necessary data)
    date_of_birth          TIMESTAMPTZ,
    age_group              VARCHAR(20),                 -- child|adolescent|adult|elderly
    preferred_language     VARCHAR(10),
    timezone               VARCHAR(50),

    -- Auth / RBAC
    email                  VARCHAR(255) UNIQUE,
    password_hash          VARCHAR(255) NOT NULL,
    role                   VARCHAR(20) NOT NULL DEFAULT 'patient',
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    last_active_at         TIMESTAMPTZ,

    -- Privacy preferences / data residency (Privacy: store in India by default)
    prefers_de_identified  BOOLEAN NOT NULL DEFAULT FALSE,
    data_residency_region  VARCHAR(10) NOT NULL DEFAULT 'in',
    data_transfer_disclosed BOOLEAN NOT NULL DEFAULT FALSE,
    anonymized             BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS consent_records (
    consent_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    purpose               VARCHAR(30) NOT NULL,        -- screening|storage|share_clinician|research
    status                VARCHAR(20) NOT NULL,        -- given|withdrawn
    consent_text_version  VARCHAR(20) NOT NULL,
    consent_text_hash     VARCHAR(64),
    recorded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    withdrawn_at          TIMESTAMPTZ,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    recorded_by           UUID REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_consent_user ON consent_records(user_id);
CREATE INDEX IF NOT EXISTS idx_consent_purpose ON consent_records(purpose);

CREATE TABLE IF NOT EXISTS screening_assessments (
    assessment_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Nullable + no FK so that high-risk / expired data can be anonymized
    -- (user_id set to NULL, linked to a pseudonymous subject_token instead).
    user_id               UUID REFERENCES users(user_id) ON DELETE CASCADE,
    subject_token         VARCHAR(64),
    is_de_identified      BOOLEAN NOT NULL DEFAULT FALSE,

    instrument_id         VARCHAR(50) NOT NULL,
    instrument_version    VARCHAR(20),
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ,
    status                VARCHAR(20) NOT NULL DEFAULT 'in_progress',

    -- Sensitive health data: encrypted at rest (never plaintext).
    encrypted_score       TEXT,
    encrypted_interpretation TEXT,

    -- Risk / retention
    high_risk             BOOLEAN NOT NULL DEFAULT FALSE,
    encrypted_high_risk_detail TEXT,
    retention_override_years INTEGER
);
CREATE INDEX IF NOT EXISTS idx_screening_assessments_user_id ON screening_assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_screening_assessments_token ON screening_assessments(subject_token);

CREATE TABLE IF NOT EXISTS screening_responses (
    response_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id            UUID NOT NULL REFERENCES screening_assessments(assessment_id) ON DELETE CASCADE,
    question_id              VARCHAR(50) NOT NULL,
    encrypted_response_value TEXT NOT NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_screening_responses_assessment_id ON screening_responses(assessment_id);

-- RBAC: clinician / care-coordinator -> patient assignments
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider_id      UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider_role    VARCHAR(20) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by       UUID REFERENCES users(user_id),
    active           BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_assignments_provider ON assignments(provider_id);
CREATE INDEX IF NOT EXISTS idx_assignments_patient ON assignments(patient_id);

-- Data-subject (erasure) requests
CREATE TABLE IF NOT EXISTS data_subject_requests (
    request_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    request_type  VARCHAR(20) NOT NULL,   -- delete|anonymize
    reason        TEXT,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',
    requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at  TIMESTAMPTZ,
    processed_by  UUID REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_dsr_user ON data_subject_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_dsr_status ON data_subject_requests(status);

-- Tamper-proof audit log (hash chain)
CREATE TABLE IF NOT EXISTS audit_logs (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seq             BIGINT NOT NULL UNIQUE,
    event_type      VARCHAR(40) NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_user_id   VARCHAR(64),
    subject_user_id VARCHAR(64),
    action          VARCHAR(40),
    resource_type   VARCHAR(40),
    resource_id     VARCHAR(120),
    metadata_json   TEXT,
    prev_hash       VARCHAR(64) NOT NULL DEFAULT 'ROOT',
    record_hash     VARCHAR(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_seq ON audit_logs(seq);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_occurred ON audit_logs(occurred_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_subject ON audit_logs(subject_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_record_hash ON audit_logs(record_hash);

-- Conversations (chat feature)
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_generating    BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_conversations_user_id UNIQUE (user_id)
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role                VARCHAR(20) NOT NULL,
    content             TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    suggested_instrument VARCHAR(50),
    suggested_at        TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
