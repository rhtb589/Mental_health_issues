-- PostgreSQL schema for the Mental Health Care platform
-- Tables defined per process.md

CREATE TABLE IF NOT EXISTS users (
    user_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_of_birth      DATE,
    age_group          VARCHAR(20),   -- child | adolescent | adult | elderly
    preferred_language VARCHAR(10),
    consent_status     VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending | given | withdrawn
    timezone           VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS screening_assessments (
    assessment_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    instrument_id      VARCHAR(50) NOT NULL,  -- e.g. PHQ9, GAD7, PHQ4, C-SSRS
    instrument_version VARCHAR(20),
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at       TIMESTAMPTZ,
    score              NUMERIC,
    interpretation     TEXT,
    status             VARCHAR(20) NOT NULL DEFAULT 'in_progress' -- in_progress | completed | abandoned
);

CREATE TABLE IF NOT EXISTS screening_responses (
    response_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID NOT NULL REFERENCES screening_assessments(assessment_id) ON DELETE CASCADE,
    question_id     VARCHAR(50) NOT NULL,
    response_value  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_screening_assessments_user_id ON screening_assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_screening_responses_assessment_id ON screening_responses(assessment_id);
