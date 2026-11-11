"""Migration 0006 on a database that already holds duplicate match_score rows (system test record, S-1)."""

import uuid

import pytest

from tests.conftest import DATABASE_URL, requires_db

pytestmark = [pytest.mark.db, requires_db]


def test_0006_keeps_the_newest_row_of_each_pair_and_then_refuses_duplicates():
    import psycopg2

    from kaziforce_api.data.migrate import migration_files

    name = f"kaziforce_test_{uuid.uuid4().hex[:8]}"
    admin = psycopg2.connect(DATABASE_URL)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {name}")
    conn = psycopg2.connect(DATABASE_URL, options=f"-c search_path={name}")
    try:
        files = migration_files()
        before = [p for p in files if p.stem < "0006"]
        (m0006,) = [p for p in files if p.stem.startswith("0006")]
        with conn, conn.cursor() as cur:
            for path in before:
                cur.execute(path.read_text())
            cur.execute("INSERT INTO worker_profile DEFAULT VALUES RETURNING worker_id")
            (worker,) = cur.fetchone()
            cur.execute("INSERT INTO job_posting DEFAULT VALUES RETURNING posting_id")
            (posting,) = cur.fetchone()
            cur.execute("INSERT INTO job_posting DEFAULT VALUES RETURNING posting_id")
            (other,) = cur.fetchone()
            # The state S-1 left behind: the same pair twice, written a moment apart, plus one clean row.
            for rank, at in ((3, "2026-11-12 00:20:15+03"), (1, "2026-11-12 00:20:16+03")):
                cur.execute("INSERT INTO match_score (fk_worker_id, fk_posting_id, composite_score, rank, created_at) "
                            "VALUES (%s, %s, 0.5, %s, %s)", (worker, posting, rank, at))
            cur.execute("INSERT INTO match_score (fk_worker_id, fk_posting_id, composite_score, rank) "
                        "VALUES (%s, %s, 0.4, 2)", (worker, other))

        with conn, conn.cursor() as cur:
            cur.execute(m0006.read_text())
            cur.execute("SELECT fk_posting_id, rank FROM match_score ORDER BY rank")
            rows = cur.fetchall()
        assert rows == [(posting, 1), (other, 2)], "the newer duplicate stays, the older goes, the clean row is kept"

        with pytest.raises(psycopg2.errors.UniqueViolation):
            with conn, conn.cursor() as cur:
                cur.execute("INSERT INTO match_score (fk_worker_id, fk_posting_id, composite_score, rank) "
                            "VALUES (%s, %s, 0.5, 4)", (worker, posting))
    finally:
        conn.close()
        with admin.cursor() as cur:
            cur.execute(f"DROP SCHEMA {name} CASCADE")
        admin.close()
