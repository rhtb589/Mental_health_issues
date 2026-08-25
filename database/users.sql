-- users table (per process.md)
CREATE TABLE IF NOT EXISTS users (
    user_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_of_birth      DATE,
    age_group          VARCHAR(20),   -- child | adolescent | adult | elderly
    preferred_language VARCHAR(10),
    consent_status     VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending | given | withdrawn
    timezone           VARCHAR(50)
);
