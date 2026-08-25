-- screening_responses table (per process.md)
CREATE TABLE IF NOT EXISTS screening_responses (
    response_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID NOT NULL REFERENCES screening_assessments(assessment_id) ON DELETE CASCADE,
    question_id     VARCHAR(50) NOT NULL,
    response_value  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_screening_responses_assessment_id ON screening_responses(assessment_id);
