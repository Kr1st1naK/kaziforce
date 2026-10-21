"""
Seeds PostgreSQL with the frozen dataset's profiles through the migrated schema.

Writes skill, worker_profile, worker_skill, job_posting and job_required_skill.
Dataset bookkeeping (group, variant, split) and ground truth never reach the
database. Seeding is idempotent: profiles are upserted by ID, their skill links
replaced, and other rows (e.g. match_score) are left alone.

skill rows:
    skill_name        the exact listed string (case kept, so profiles round-trip exactly)
    esco_code         ESCO skill URI for an exact ESCO skill label; for an informal term in the
                      knowledge graph, the ESCO occupation it maps to; otherwise NULL
    is_informal_term  true for every accepted alias, including the withheld ones, which keep
                      esco_code NULL so the database maps them to nothing
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from psycopg2.extras import execute_values

from kaziforce_api.data.loaders import DATA_DIR
from kaziforce_api.data.models import JobPosting, WorkerProfile
from kaziforce_kg.vocabulary import VocabularyExtension


@dataclass(frozen=True)
class SkillRow:
    skill_name: str
    esco_code: str | None
    is_informal_term: bool


class SkillDescriber:
    """Describes listed skill strings for the skill table. Built once and reused (the lookups are read from disk)."""

    def __init__(self, vocabulary: VocabularyExtension | None = None, kg_dir: Path = DATA_DIR / "kg"):
        vocabulary = vocabulary or VocabularyExtension()
        with open(Path(kg_dir) / "skills.csv", newline="", encoding="utf-8") as f:
            self.esco = {r["label"]: r["uri"] for r in csv.DictReader(f)}
        self.included = {t["alias"]: t["esco_uri"] for t in vocabulary.kg_terms()}
        self.withheld = {t["alias"] for t in vocabulary.held_out_terms()}

    def describe(self, names: Iterable[str]) -> list[SkillRow]:
        """One row per distinct string, in first-seen order."""
        return [SkillRow(n, self.esco.get(n) or self.included.get(n), n in self.included or n in self.withheld)
                for n in dict.fromkeys(names)]


def skill_rows(workers: Sequence[WorkerProfile], jobs: Sequence[JobPosting],
               vocabulary: VocabularyExtension | None = None, kg_dir: Path = DATA_DIR / "kg") -> list[SkillRow]:
    return SkillDescriber(vocabulary, kg_dir).describe(
        [*(s for w in workers for s in w.skills), *(s for j in jobs for s in j.required_skills)])


def reset(conn) -> dict:
    """Delete every profile, posting, skill and match score, so the database can be re-seeded clean.

    Use after a demo or an end-to-end run, which store real profiles and postings through the API.
    """
    tables = ("match_score", "worker_skill", "job_required_skill", "worker_profile", "job_posting", "skill")
    deleted = {}
    with conn, conn.cursor() as cur:
        for table in tables:
            cur.execute(f"DELETE FROM {table}")
            deleted[table] = cur.rowcount
    return deleted


def seed(conn, workers: Sequence[WorkerProfile], jobs: Sequence[JobPosting], skills: Sequence[SkillRow]) -> dict:
    """Write everything in one transaction; returns row counts written."""
    with conn, conn.cursor() as cur:
        rows = execute_values(cur, "INSERT INTO skill (skill_name, esco_code, is_informal_term) VALUES %s "
                                   "ON CONFLICT (skill_name) DO UPDATE SET esco_code = EXCLUDED.esco_code, "
                                   "is_informal_term = EXCLUDED.is_informal_term RETURNING skill_name, skill_id",
                              [(s.skill_name, s.esco_code, s.is_informal_term) for s in skills], fetch=True)
        skill_id = dict(rows)

        execute_values(cur, "INSERT INTO worker_profile (worker_id, biography, location, availability, "
                            "rate_expectation) VALUES %s ON CONFLICT (worker_id) DO UPDATE SET "
                            "biography = EXCLUDED.biography, location = EXCLUDED.location, "
                            "availability = EXCLUDED.availability, rate_expectation = EXCLUDED.rate_expectation",
                       [(w.worker_id, w.biography, w.location, w.availability, w.rate_expectation) for w in workers])
        cur.execute("DELETE FROM worker_skill WHERE fk_worker_id = ANY(%s::uuid[])", ([w.worker_id for w in workers],))
        worker_links = [(w.worker_id, skill_id[s], i) for w in workers for i, s in enumerate(w.skills)]
        execute_values(cur, "INSERT INTO worker_skill (fk_worker_id, fk_skill_id, position) VALUES %s", worker_links)

        execute_values(cur, "INSERT INTO job_posting (posting_id, title, description, budget, location, availability) "
                            "VALUES %s ON CONFLICT (posting_id) DO UPDATE SET title = EXCLUDED.title, "
                            "description = EXCLUDED.description, budget = EXCLUDED.budget, "
                            "location = EXCLUDED.location, availability = EXCLUDED.availability",
                       [(j.posting_id, j.title, j.description, j.budget, j.location, j.availability) for j in jobs])
        cur.execute("DELETE FROM job_required_skill WHERE fk_posting_id = ANY(%s::uuid[])", ([j.posting_id for j in jobs],))
        job_links = [(j.posting_id, skill_id[s], i) for j in jobs for i, s in enumerate(j.required_skills)]
        execute_values(cur, "INSERT INTO job_required_skill (fk_posting_id, fk_skill_id, position) VALUES %s", job_links)
    return {"skill": len(skills), "worker_profile": len(workers), "worker_skill": len(worker_links),
            "job_posting": len(jobs), "job_required_skill": len(job_links)}
