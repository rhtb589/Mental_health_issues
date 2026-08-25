-- screening_assessments table (per process.md)
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

CREATE INDEX IF NOT EXISTS idx_screening_assessments_user_id ON screening_assessments(user_id);
