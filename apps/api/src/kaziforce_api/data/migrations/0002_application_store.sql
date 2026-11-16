-- 0002: make the schema hold the application's profiles exactly (#41).
--
-- job_posting gains title and availability, which postings carry and the scorers use.
-- The skill link tables gain position, so a profile's skills come back in the order
-- given (the round-trip test compares full records, skills included).
-- match_score records which configuration produced it, and composite is widened:
-- BM25 keyword scores are not bounded by 1 (development maximum about 89).
-- The tables were empty when this migration was written; the NOT NULL columns
-- assume no existing link rows.

ALTER TABLE job_posting
    ADD COLUMN title         VARCHAR(255),
    ADD COLUMN availability  VARCHAR(50);

ALTER TABLE worker_skill
    ADD COLUMN position INTEGER NOT NULL CHECK (position >= 0),
    ADD CONSTRAINT worker_skill_position_unique UNIQUE (fk_worker_id, position);

ALTER TABLE job_required_skill
    ADD COLUMN position INTEGER NOT NULL CHECK (position >= 0),
    ADD CONSTRAINT job_required_skill_position_unique UNIQUE (fk_posting_id, position);

ALTER TABLE match_score
    ADD COLUMN configuration VARCHAR(50) NOT NULL DEFAULT 'full',
    ALTER COLUMN composite_score TYPE NUMERIC(12, 5);
