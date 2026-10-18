"""PostgreSQL round trip: profiles read back from the database equal the evaluation CSVs, field for field.

Runs only when DATABASE_URL is set (skipped in CI, which has no database). Works in a
throwaway schema that it creates, migrates, seeds and drops, so existing tables are untouched.
"""

import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()
pytestmark = [pytest.mark.db,
              pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set (no database)")]

from kaziforce_api.data.data_loader import DataLoader  # noqa: E402
from kaziforce_api.data.migrate import migration_files  # noqa: E402
from kaziforce_api.data.models import MatchScore  # noqa: E402
from kaziforce_api.data.seed import seed, skill_rows  # noqa: E402
from kaziforce_api.data.store import PostgresProfileStore  # noqa: E402


@pytest.fixture(scope="module")
def schema():
    import psycopg2

    name = f"kaziforce_test_{uuid.uuid4().hex[:8]}"
    url = os.environ["DATABASE_URL"]
    admin = psycopg2.connect(url)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {name}")

    def connect():
        return psycopg2.connect(url, options=f"-c search_path={name}")

    conn = connect()
    with conn, conn.cursor() as cur:
        for path in migration_files():
            cur.execute(path.read_text())
    conn.close()
    try:
        yield connect
    finally:
        with admin.cursor() as cur:
            cur.execute(f"DROP SCHEMA {name} CASCADE")
        admin.close()


@pytest.fixture(scope="module")
def seeded(schema):
    loader = DataLoader()
    workers, jobs = loader.workers("development"), loader.jobs()
    conn = schema()
    counts = seed(conn, workers, jobs, skill_rows(workers, jobs))
    conn.close()
    return loader, workers, jobs, counts, PostgresProfileStore(schema)


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


def test_seeding_is_idempotent(seeded, schema):
    loader, workers, jobs, counts, store = seeded
    conn = schema()
    assert seed(conn, workers, jobs, skill_rows(workers, jobs)) == counts
    with conn.cursor() as cur:
        for table in ("skill", "worker_profile", "worker_skill", "job_posting", "job_required_skill"):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == counts[table], table
    conn.close()
    assert {w.worker_id: w for w in store.workers()} == {w.worker_id: w for w in workers}


def test_no_bookkeeping_or_labels_and_withheld_aliases_map_to_nothing(seeded, schema):
    conn = schema()
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


def test_match_scores_are_written_with_nulls_and_unbounded_keyword_scores(seeded, schema):
    _, workers, jobs, _, store = seeded
    w = workers[0]
    scores = [MatchScore(w.worker_id, jobs[0].posting_id, composite=88.95123, rank=1),
              MatchScore(w.worker_id, jobs[1].posting_id, composite=0.7, rule=0.8, semantic=0.6, rank=2)]
    assert store.save_match_scores(w.worker_id, "keyword", scores) == 2
    conn = schema()
    with conn.cursor() as cur:
        cur.execute("SELECT rank, composite_score, rule_score, semantic_score, configuration FROM match_score "
                    "WHERE fk_worker_id = %s ORDER BY rank", (w.worker_id,))
        rows = cur.fetchall()
    conn.close()
    assert [(r, float(c), rule, sem, cfg) for r, c, rule, sem, cfg in rows][0] == (1, 88.95123, None, None, "keyword")
    assert float(rows[1][2]) == 0.8


def test_unknown_or_malformed_worker_id_is_a_key_error(seeded):
    store = seeded[-1]
    for worker_id in (str(uuid.uuid4()), "not-a-uuid"):
        with pytest.raises(KeyError):
            store.worker(worker_id)
