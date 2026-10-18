"""
Profile stores: where the application reads worker profiles and job postings.

PostgresProfileStore is the application store (the CLI and the API read from
it). CsvProfileStore reads the frozen dataset through DataLoader and stays
available for environments without a database, such as CI. The evaluation
always reads the CSVs through DataLoader directly, so results stay traceable
through the manifest checksums.

Both stores return the same WorkerProfile / JobPosting objects; the
round-trip test (tests/test_store.py) checks they are field-for-field equal.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.models import JobPosting, MatchScore, WorkerProfile


class ProfileStore(ABC):
    @abstractmethod
    def jobs(self) -> list[JobPosting]: ...

    @abstractmethod
    def workers(self) -> list[WorkerProfile]: ...

    @abstractmethod
    def worker(self, worker_id: str) -> WorkerProfile:
        """The stored worker; KeyError if there is none."""


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

    def jobs(self) -> list[JobPosting]:
        return [JobPosting(pid, title or "", description, tuple(skills), location, availability, _float(budget))
                for pid, title, description, location, availability, budget, skills in self._query(_JOB_SQL)]

    def save_match_scores(self, worker_id: str, configuration: str, scores: Sequence[MatchScore]) -> int:
        """Record a ranking as MatchScore rows (one per ranked posting); returns the number written."""
        rows = [(worker_id, m.posting_id, m.rule, m.semantic, m.composite, m.rank, configuration) for m in scores]
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.executemany("INSERT INTO match_score (fk_worker_id, fk_posting_id, rule_score, semantic_score, "
                                "composite_score, rank, configuration) VALUES (%s, %s, %s, %s, %s, %s, %s)", rows)
        finally:
            conn.close()
        return len(rows)
