-- 0001: initial relational schema — proposal Figure 4.6 (Database Design).
--
-- Entity -> table: WorkerProfile -> worker_profile, JobPosting -> job_posting,
-- Skill -> skill, WorkerSkill -> worker_skill, JobRequiredSkill ->
-- job_required_skill, MatchScore -> match_score.
-- Figure 4.6 labels MatchScore's worker FK "fk_woker_id"; implemented as fk_worker_id.
--
-- Prerequisite (superuser, once per database): CREATE EXTENSION IF NOT EXISTS vector;
-- Apply with: python -m kaziforce_api.data.migrate

CREATE TABLE skill (
    skill_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name        VARCHAR(255) NOT NULL UNIQUE,
    esco_code         VARCHAR(255),              -- ESCO concept URI (informal terms: the URI they map to)
    is_informal_term  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE worker_profile (
    worker_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    biography         TEXT,
    location          VARCHAR(255),
    availability      VARCHAR(50),
    rate_expectation  NUMERIC(12, 2),            -- KES
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE job_posting (
    posting_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category          VARCHAR(255),
    description       TEXT,
    budget            NUMERIC(12, 2),            -- KES
    location          VARCHAR(255),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE worker_skill (
    fk_worker_id      UUID NOT NULL REFERENCES worker_profile (worker_id) ON DELETE CASCADE,
    fk_skill_id       UUID NOT NULL REFERENCES skill (skill_id) ON DELETE CASCADE,
    PRIMARY KEY (fk_worker_id, fk_skill_id)
);

CREATE TABLE job_required_skill (
    fk_posting_id     UUID NOT NULL REFERENCES job_posting (posting_id) ON DELETE CASCADE,
    fk_skill_id       UUID NOT NULL REFERENCES skill (skill_id) ON DELETE CASCADE,
    PRIMARY KEY (fk_posting_id, fk_skill_id)
);

CREATE TABLE match_score (
    match_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_worker_id      UUID NOT NULL REFERENCES worker_profile (worker_id) ON DELETE CASCADE,
    fk_posting_id     UUID NOT NULL REFERENCES job_posting (posting_id) ON DELETE CASCADE,
    rule_score        NUMERIC(6, 5),
    semantic_score    NUMERIC(6, 5),
    composite_score   NUMERIC(6, 5),
    rank              INTEGER CHECK (rank >= 1),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Reverse lookups for the composite/foreign keys
CREATE INDEX worker_skill_skill_idx       ON worker_skill (fk_skill_id);
CREATE INDEX job_required_skill_skill_idx ON job_required_skill (fk_skill_id);
CREATE INDEX match_score_worker_idx       ON match_score (fk_worker_id);
CREATE INDEX match_score_posting_idx      ON match_score (fk_posting_id);
