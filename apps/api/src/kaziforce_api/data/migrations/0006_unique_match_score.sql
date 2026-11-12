-- 0006: one match_score row per (worker, posting, configuration).
--
-- Two /recommend calls for the same worker at the same moment could each delete the previous
-- ranking before either inserted its own, so both rankings survived side by side (system test
-- record, S-1). The store now serialises those writes; this constraint makes a duplicate
-- impossible whatever writes the table.
--
-- Existing duplicates are removed first, keeping the most recent row of each pair (latest
-- created_at, then the larger match_id as a tie-break), so the constraint can be added to a
-- database that already holds them. Only rows that duplicate another are deleted.
--
-- To undo it: ALTER TABLE match_score DROP CONSTRAINT match_score_pair_unique;
-- (the deleted duplicates are not restored; they were copies of a ranking that was replaced).

DELETE FROM match_score AS m
USING match_score AS newer
WHERE m.fk_worker_id = newer.fk_worker_id
  AND m.fk_posting_id = newer.fk_posting_id
  AND m.configuration = newer.configuration
  AND (m.created_at, m.match_id::text) < (newer.created_at, newer.match_id::text);

ALTER TABLE match_score
    ADD CONSTRAINT match_score_pair_unique UNIQUE (fk_worker_id, fk_posting_id, configuration);
