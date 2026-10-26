-- 0003: accounts, sessions, and ownership of profiles and postings.
--
-- A worker account owns at most one worker profile; a client account owns many
-- job postings. Both ownership columns are NULLable, so the frozen dataset
-- (216 worker profiles, 280 postings) still seeds with no account attached.
--
-- The PIN is stored only as a PBKDF2-HMAC-SHA256 hash with a per-account salt;
-- the PIN itself is never stored, logged or returned. The session cookie value
-- is likewise stored only as a SHA-256 hash, so a database copy does not hand
-- over usable sessions. See docs/limitations.md for what this does not protect
-- against: a 4-digit PIN has 10,000 combinations.
--
-- Apply with: python -m kaziforce_api.data.migrate

CREATE TABLE account (
    account_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone             VARCHAR(20) NOT NULL UNIQUE,      -- E.164 without "+", e.g. 254712345678
    role              VARCHAR(10) NOT NULL CHECK (role IN ('worker', 'client')),
    pin_hash          TEXT NOT NULL,
    pin_salt          TEXT NOT NULL,
    pin_iterations    INTEGER NOT NULL,
    failed_attempts   INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    locked_until      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE session (
    token_hash        CHAR(64) PRIMARY KEY,             -- sha256 of the cookie value
    fk_account_id     UUID NOT NULL REFERENCES account (account_id) ON DELETE CASCADE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at        TIMESTAMPTZ NOT NULL
);

CREATE INDEX session_account_idx ON session (fk_account_id);

ALTER TABLE worker_profile
    ADD COLUMN fk_account_id UUID REFERENCES account (account_id) ON DELETE CASCADE;

-- One profile per worker account. Seeded profiles have no account and are unaffected.
CREATE UNIQUE INDEX worker_profile_account_unique ON worker_profile (fk_account_id)
    WHERE fk_account_id IS NOT NULL;

ALTER TABLE job_posting
    ADD COLUMN fk_account_id UUID REFERENCES account (account_id) ON DELETE CASCADE;

CREATE INDEX job_posting_account_idx ON job_posting (fk_account_id);
