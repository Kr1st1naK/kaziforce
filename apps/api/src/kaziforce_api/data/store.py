"""
Profile stores: where the application reads worker profiles and job postings.

PostgresProfileStore is the application store (the CLI and the API read from
it). CsvProfileStore reads the frozen dataset through DataLoader and stays
available for environments without a database, such as CI. The evaluation
always reads the CSVs through DataLoader directly, so results stay traceable
through the manifest checksums.

Both stores return the same WorkerProfile / JobPosting objects; the
round-trip test (tests/test_store.py) checks they are field-for-field equal.

Only PostgresProfileStore can store new profiles; CsvProfileStore raises
ReadOnlyStore, because the committed dataset is frozen.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import replace

from psycopg2.extras import execute_values

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.models import JobPosting, MatchScore, WorkerProfile
from kaziforce_api.data.seed import SkillRow


class ReadOnlyStore(RuntimeError):
    """Raised when a store cannot accept new profiles."""


class ProfileStore(ABC):
    @abstractmethod
    def jobs(self) -> list[JobPosting]: ...

    @abstractmethod
    def workers(self) -> list[WorkerProfile]: ...

    @abstractmethod
    def worker(self, worker_id: str) -> WorkerProfile:
        """The stored worker; KeyError if there is none."""

    @abstractmethod
    def job(self, posting_id: str) -> JobPosting:
        """The stored posting; KeyError if there is none."""

    def save_worker(self, profile: WorkerProfile, skills: Sequence[SkillRow]) -> WorkerProfile:
        """Store a new worker profile and return it with the identifier it was given."""
        raise ReadOnlyStore(f"{type(self).__name__} cannot store new worker profiles")

    def save_job(self, posting: JobPosting, skills: Sequence[SkillRow]) -> JobPosting:
        """Store a new job posting and return it with the identifier it was given."""
        raise ReadOnlyStore(f"{type(self).__name__} cannot store new job postings")

    def save_match_scores(self, worker_id: str, configuration: str, scores: Sequence[MatchScore],
                          replace: bool = False) -> int:
        """Record a ranking. A store that cannot write says so; the caller decides whether to care."""
        raise ReadOnlyStore(f"{type(self).__name__} cannot store match scores")


class CsvProfileStore(ProfileStore):
    """The frozen dataset's development-split workers and all postings."""

    def __init__(self, loader: DataLoader | None = None, split: str = "development"):
        self.loader, self.split = loader or DataLoader(), split

    def jobs(self) -> list[JobPosting]:
        return self.loader.jobs()

    def workers(self) -> list[WorkerProfile]:
        return self.loader.workers(self.split)

    def worker(self, worker_id: str) -> WorkerProfile:
        return self.loader.worker(worker_id, self.split)

    def job(self, posting_id: str) -> JobPosting:
        for j in self.jobs():
            if j.posting_id == posting_id:
                return j
        raise KeyError(posting_id)


def _float(value) -> float | None:
    return float(value) if value is not None else None


_WORKER_SQL = """
    SELECT w.worker_id::text, w.biography, w.location, w.availability, w.rate_expectation,
           COALESCE(array_agg(s.skill_name ORDER BY ws.position) FILTER (WHERE s.skill_name IS NOT NULL), ARRAY[]::text[])
    FROM worker_profile w
    LEFT JOIN worker_skill ws ON ws.fk_worker_id = w.worker_id
    LEFT JOIN skill s ON s.skill_id = ws.fk_skill_id
    {where}
    GROUP BY w.worker_id ORDER BY w.worker_id
"""
_JOB_SQL = """
    SELECT p.posting_id::text, p.title, p.description, p.location, p.availability, p.budget,
           COALESCE(array_agg(s.skill_name ORDER BY r.position) FILTER (WHERE s.skill_name IS NOT NULL), ARRAY[]::text[])
    FROM job_posting p
    LEFT JOIN job_required_skill r ON r.fk_posting_id = p.posting_id
    LEFT JOIN skill s ON s.skill_id = r.fk_skill_id
    {where}
    GROUP BY p.posting_id ORDER BY p.posting_id
"""


class PostgresProfileStore(ProfileStore):
    """The application store. Connects lazily: constructing it never touches the database."""

    def __init__(self, connect: Callable | None = None):
        if connect is None:
            from kaziforce_api.data.db import get_connection as connect
        self._connect = connect

    def _query(self, sql: str, params: Sequence = ()) -> list[tuple]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def _worker(row) -> WorkerProfile:
        worker_id, biography, location, availability, rate, skills = row
        return WorkerProfile(worker_id, biography, tuple(skills), location, availability, _float(rate))

    def workers(self) -> list[WorkerProfile]:
        return [self._worker(r) for r in self._query(_WORKER_SQL.format(where=""))]

    def worker(self, worker_id: str) -> WorkerProfile:
        try:
            uuid.UUID(worker_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(worker_id) from None
        rows = self._query(_WORKER_SQL.format(where="WHERE w.worker_id = %s"), (worker_id,))
        if not rows:
            raise KeyError(worker_id)
        return self._worker(rows[0])

    @staticmethod
    def _job(row) -> JobPosting:
        pid, title, description, location, availability, budget, skills = row
        return JobPosting(pid, title or "", description, tuple(skills), location, availability, _float(budget))

    def jobs(self) -> list[JobPosting]:
        return [self._job(r) for r in self._query(_JOB_SQL.format(where=""))]

    def job(self, posting_id: str) -> JobPosting:
        try:
            uuid.UUID(posting_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(posting_id) from None
        rows = self._query(_JOB_SQL.format(where="WHERE p.posting_id = %s"), (posting_id,))
        if not rows:
            raise KeyError(posting_id)
        return self._job(rows[0])

    # Writes

    def _skill_ids(self, cur, skills: Sequence[SkillRow]) -> dict[str, str]:
        if not skills:
            return {}
        rows = execute_values(cur, "INSERT INTO skill (skill_name, esco_code, is_informal_term) VALUES %s "
                                   "ON CONFLICT (skill_name) DO UPDATE SET esco_code = EXCLUDED.esco_code, "
                                   "is_informal_term = EXCLUDED.is_informal_term RETURNING skill_name, skill_id",
                              [(s.skill_name, s.esco_code, s.is_informal_term) for s in skills], fetch=True)
        return dict(rows)

    def save_worker(self, profile: WorkerProfile, skills: Sequence[SkillRow]) -> WorkerProfile:
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                skill_id = self._skill_ids(cur, skills)
                cur.execute("INSERT INTO worker_profile (biography, location, availability, rate_expectation) "
                            "VALUES (%s, %s, %s, %s) RETURNING worker_id::text",
                            (profile.biography, profile.location, profile.availability, profile.rate_expectation))
                worker_id = cur.fetchone()[0]
                execute_values(cur, "INSERT INTO worker_skill (fk_worker_id, fk_skill_id, position) VALUES %s",
                               [(worker_id, skill_id[s], i) for i, s in enumerate(profile.skills)])
        finally:
            conn.close()
        return replace(profile, worker_id=worker_id)

    def save_job(self, posting: JobPosting, skills: Sequence[SkillRow]) -> JobPosting:
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                skill_id = self._skill_ids(cur, skills)
                cur.execute("INSERT INTO job_posting (title, description, budget, location, availability) "
                            "VALUES (%s, %s, %s, %s, %s) RETURNING posting_id::text",
                            (posting.title, posting.description, posting.budget, posting.location,
                             posting.availability))
                posting_id = cur.fetchone()[0]
                execute_values(cur, "INSERT INTO job_required_skill (fk_posting_id, fk_skill_id, position) VALUES %s",
                               [(posting_id, skill_id[s], i) for i, s in enumerate(posting.required_skills)])
        finally:
            conn.close()
        return replace(posting, posting_id=posting_id)

    def save_match_scores(self, worker_id: str, configuration: str, scores: Sequence[MatchScore],
                          replace: bool = False) -> int:
        """Record a ranking as MatchScore rows (one per ranked posting); returns the number written.

        `replace` drops this worker's previous ranking under the same configuration first, so the
        table holds the current ranking rather than one row per time anybody looked. The API uses
        it; a batch run that wants a history does not.
        """
        rows = [(worker_id, m.posting_id, m.rule, m.semantic, m.composite, m.rank, configuration) for m in scores]
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                if replace:
                    cur.execute("DELETE FROM match_score WHERE fk_worker_id = %s AND configuration = %s",
                                (worker_id, configuration))
                cur.executemany("INSERT INTO match_score (fk_worker_id, fk_posting_id, rule_score, semantic_score, "
                                "composite_score, rank, configuration) VALUES (%s, %s, %s, %s, %s, %s, %s)", rows)
        finally:
            conn.close()
        return len(rows)
