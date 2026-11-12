"""PostgreSQL round trip: profiles read back from the database equal the evaluation CSVs, field for field.

Runs only when DATABASE_URL is set (skipped in CI, which has no database). Works in a
throwaway schema that it creates, migrates, seeds and drops, so existing tables are untouched.
"""

import uuid

import pytest

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.models import JobPosting, MatchScore
from kaziforce_api.data.seed import seed, skill_rows
from kaziforce_api.data.store import PostgresProfileStore
from tests.conftest import requires_db

pytestmark = [pytest.mark.db, requires_db]


@pytest.fixture(scope="module")
def seeded(pg_connect):
    loader = DataLoader()
    workers, jobs = loader.workers("development"), loader.jobs()
    conn = pg_connect()
    counts = seed(conn, workers, jobs, skill_rows(workers, jobs))
    conn.close()
    return loader, workers, jobs, counts, PostgresProfileStore(pg_connect)


def test_every_worker_round_trips_field_for_field(seeded):
    loader, workers, _, _, store = seeded
    stored = {w.worker_id: w for w in store.workers()}
    assert len(stored) == len(workers) == 216
    for w in workers:
        assert stored[w.worker_id] == w  # all fields, skills in order, None for missing
        assert store.worker(w.worker_id) == w


def test_every_posting_round_trips_field_for_field(seeded):
    _, _, jobs, _, store = seeded
    stored = {j.posting_id: j for j in store.jobs()}
    assert stored == {j.posting_id: j for j in jobs} and len(stored) == 280


def test_seeding_is_idempotent(seeded, pg_connect):
    loader, workers, jobs, counts, store = seeded
    conn = pg_connect()
    assert seed(conn, workers, jobs, skill_rows(workers, jobs)) == counts
    with conn.cursor() as cur:
        for table in ("skill", "worker_profile", "worker_skill", "job_posting", "job_required_skill"):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == counts[table], table
    conn.close()
    assert {w.worker_id: w for w in store.workers()} == {w.worker_id: w for w in workers}


def test_no_bookkeeping_or_labels_and_withheld_aliases_map_to_nothing(seeded, pg_connect):
    conn = pg_connect()
    with conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema()")
        columns = {r[0] for r in cur.fetchall()}
        assert not columns & {"group_id", "variant", "split", "area", "area_id", "relevant"}
        cur.execute("SELECT skill_name, esco_code, is_informal_term FROM skill "
                    "WHERE skill_name IN ('fundi wa stima', 'mshonaji', 'fundi wa umeme')")
        rows = {name: (code, informal) for name, code, informal in cur.fetchall()}
    conn.close()
    assert rows["fundi wa stima"] == (None, True) and rows["mshonaji"] == (None, True)
    assert rows["fundi wa umeme"][0].startswith("http://data.europa.eu/esco/occupation/")


def test_match_scores_are_written_with_nulls_and_unbounded_keyword_scores(seeded, pg_connect):
    _, workers, jobs, _, store = seeded
    w = workers[0]
    scores = [MatchScore(w.worker_id, jobs[0].posting_id, composite=88.95123, rank=1),
              MatchScore(w.worker_id, jobs[1].posting_id, composite=0.7, rule=0.8, semantic=0.6, rank=2)]
    assert store.save_match_scores(w.worker_id, "keyword", scores) == 2
    conn = pg_connect()
    with conn.cursor() as cur:
        cur.execute("SELECT rank, composite_score, rule_score, semantic_score, configuration FROM match_score "
                    "WHERE fk_worker_id = %s ORDER BY rank", (w.worker_id,))
        rows = cur.fetchall()
    conn.close()
    assert [(r, float(c), rule, sem, cfg) for r, c, rule, sem, cfg in rows][0] == (1, 88.95123, None, None, "keyword")
    assert float(rows[1][2]) == 0.8


def _ranking(store_rows):
    """Rows as (rank, posting) pairs; a single clean ranking has ranks 1..n and n distinct postings."""
    ranks = sorted(r for r, _ in store_rows)
    postings = {p for _, p in store_rows}
    return ranks, postings


def test_concurrent_replacements_leave_exactly_one_ranking(seeded, pg_connect):
    """S-1 (system test record): two requests replacing the same worker's ranking at once.

    Each call deletes the worker's ranking and inserts its own. Without serialisation, both
    deletes can run before either insert commits, and both rankings survive side by side.
    """
    import threading

    _, workers, jobs, _, store = seeded
    w = workers[1]
    for round_ in range(5):
        sizes = [5, 8, 5, 8]
        barrier = threading.Barrier(len(sizes))
        errors = []

        def save(k):
            scores = [MatchScore(w.worker_id, jobs[i].posting_id, composite=1 - i / 100, rule=0.5, semantic=0.5,
                                 rank=i + 1) for i in range(k)]
            try:
                barrier.wait()
                store.save_match_scores(w.worker_id, "full", scores, replace=True)
            except Exception as e:  # surfaced below, so a failing thread fails the test
                errors.append(e)

        threads = [threading.Thread(target=save, args=(k,)) for k in sizes]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, errors

        conn = pg_connect()
        with conn.cursor() as cur:
            cur.execute("SELECT rank, fk_posting_id::text FROM match_score "
                        "WHERE fk_worker_id = %s AND configuration = 'full'", (w.worker_id,))
            rows = cur.fetchall()
        conn.close()
        ranks, postings = _ranking(rows)
        assert len(rows) in (5, 8), f"round {round_}: {len(rows)} rows"
        assert ranks == list(range(1, len(rows) + 1)), f"round {round_}: ranks {ranks}"
        assert len(postings) == len(rows)


def test_the_database_refuses_a_second_row_for_the_same_pair(seeded, pg_connect):
    """Migration 0006: one row per (worker, posting, configuration), whatever writes it."""
    import psycopg2

    _, workers, jobs, _, _ = seeded
    w, j = workers[2], jobs[0]
    conn = pg_connect()
    with pytest.raises(psycopg2.errors.UniqueViolation):
        with conn, conn.cursor() as cur:
            for _ in range(2):
                cur.execute("INSERT INTO match_score (fk_worker_id, fk_posting_id, composite_score, rank, configuration) "
                            "VALUES (%s, %s, 0.5, 1, 'full')", (w.worker_id, j.posting_id))
    conn.close()


def test_unknown_or_malformed_worker_id_is_a_key_error(seeded):
    store = seeded[-1]
    for worker_id in (str(uuid.uuid4()), "not-a-uuid"):
        with pytest.raises(KeyError):
            store.worker(worker_id)


def test_reset_empties_every_table_so_a_demo_can_start_clean(pg_connect):
    """Profiles and postings stored through the API are cleared, and re-seeding restores the frozen dataset."""
    from kaziforce_api.data.seed import reset

    loader = DataLoader()
    workers, jobs = loader.workers("development"), loader.jobs()
    store = PostgresProfileStore(pg_connect)
    conn = pg_connect()
    seed(conn, workers, jobs, skill_rows(workers, jobs))
    conn.close()

    posting = JobPosting("", "Demo posting", "Added during a demo", ("splice cable",), None, None, None)
    extra = store.save_job(posting, skill_rows([], [posting]))
    assert len(store.jobs()) == len(jobs) + 1

    conn = pg_connect()
    deleted = reset(conn)
    conn.close()
    assert deleted["worker_profile"] == len(workers) and deleted["job_posting"] == len(jobs) + 1
    assert store.jobs() == [] and store.workers() == []

    conn = pg_connect()
    seed(conn, workers, jobs, skill_rows(workers, jobs))
    conn.close()
    assert {j.posting_id for j in store.jobs()} == {j.posting_id for j in jobs}
    assert extra.posting_id not in {j.posting_id for j in store.jobs()}
