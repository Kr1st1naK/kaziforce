"""Storing profiles through the API, against a real PostgreSQL schema (skipped without DATABASE_URL)."""

import pytest

from kaziforce_api.app import create_app
from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.loaders import load_synthetic_ground_truth
from kaziforce_api.data.seed import seed, skill_rows
from kaziforce_api.data.store import PostgresProfileStore
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_api.service import RecommendationService
from tests.conftest import requires_db

pytestmark = [pytest.mark.db, requires_db]

WORKER = {"biography": "Mimi ni fundi wa umeme, niko Nyeri.", "skills": ["fundi wa umeme"],
          "location": "Nyeri", "availability": "Part-time", "rate_expectation": 2000}
JOB = {"title": "Rewire a small shop", "description": "We need an electrician in Nyeri to rewire a small shop.",
       "required_skills": ["install electricity sockets", "splice cable"], "location": "Nyeri",
       "availability": "Part-time", "budget": 2600}


@pytest.fixture(scope="module")
def client(pg_connect, stub_encoder):
    loader = DataLoader()
    workers, jobs = loader.workers("development"), loader.jobs()
    conn = pg_connect()
    seed(conn, workers, jobs, skill_rows(workers, jobs))
    conn.close()
    service = RecommendationService(PostgresProfileStore(pg_connect),
                                    semantic_factory=lambda: SemanticScorer(encoder=stub_encoder))
    return create_app(service.start(background=False)).test_client()


def test_a_stored_worker_can_then_be_recommended_for(client):
    created = client.post("/workers", json=WORKER)
    assert created.status_code == 201
    d = created.get_json()
    worker_id = d["worker_id"]
    assert worker_id and d["worker"] == {"worker_id": worker_id, **WORKER}
    assert [o["label"] for o in d["enrichment"]["occupations"]] == ["electrician"]

    ranked = client.post("/recommend", json={"worker_id": worker_id, "k": 5})
    assert ranked.status_code == 200
    results = ranked.get_json()["results"]
    assert len(results) == 5 and results[0]["matched_skills"]


def test_an_unrecognised_term_is_stored_and_reported_as_unmapped(client):
    d = client.post("/workers", json={"biography": "Mimi ni fundi wa stima.", "skills": ["fundi wa stima"]}).get_json()
    assert d["enrichment"] == {"terms": [], "occupations": [], "unmapped": ["fundi wa stima"]}
    assert client.post("/recommend", json={"worker_id": d["worker_id"], "k": 3}).status_code == 200


def test_a_posted_job_joins_the_candidate_pool_and_can_be_recommended(client):
    before = client.get("/health").get_json()["candidate_jobs"]
    created = client.post("/jobs", json=JOB)
    assert created.status_code == 201
    d = created.get_json()
    posting_id = d["posting_id"]
    assert d["candidate_jobs"] == before + 1
    assert client.get("/health").get_json()["candidate_jobs"] == before + 1

    worker_id = client.post("/workers", json=WORKER).get_json()["worker_id"]
    ranked = client.post("/recommend", json={"worker_id": worker_id, "k": 50}).get_json()
    assert posting_id in [r["posting_id"] for r in ranked["results"]]


def test_the_interpretation_reports_stated_skills_and_a_worker_pool(client):
    d = client.post("/jobs", json=JOB).get_json()
    interpretation = d["interpretation"]
    assert [o["label"] for o in interpretation["occupations"]] == ["electrician"]
    assert [s["skill_label"] for s in interpretation["stated_skills"]] == JOB["required_skills"]
    assert all(s["source"] == "listed" for s in interpretation["stated_skills"])

    # Counted from the profiles themselves. Independently: the development-split workers whose
    # ground-truth area is Electrician, excluding held_out variants, whose alias the graph cannot map.
    truth = load_synthetic_ground_truth()["worker_truth"]
    stored = {w.worker_id for w in DataLoader().workers("development")}
    expected = len(truth[truth.worker_id.isin(stored) & (truth.area_id == "1") & (truth.variant != "held_out")])
    (pool,) = [p for p in interpretation["worker_pool"] if p["occupation"]["label"] == "electrician"]
    assert pool["workers"] >= expected  # profiles added by other tests in this module may add more


def test_the_stored_posting_reads_back_the_same_way(client):
    posting_id = client.post("/jobs", json=JOB).get_json()["posting_id"]
    fetched = client.get(f"/jobs/{posting_id}")
    assert fetched.status_code == 200
    d = fetched.get_json()
    assert d["job"] == {"posting_id": posting_id, **JOB}
    assert d["interpretation"]["stated_skills"]


def test_a_posting_without_a_budget_or_availability_scores_those_criteria_as_null(client):
    sparse = {"title": "Fix a socket", "description": "A socket needs fixing in Thika.",
              "required_skills": ["install electricity sockets"]}
    posting_id = client.post("/jobs", json=sparse).get_json()["posting_id"]
    worker_id = client.post("/workers", json=WORKER).get_json()["worker_id"]
    results = client.post("/recommend", json={"worker_id": worker_id, "k": 50}).get_json()["results"]
    (result,) = [r for r in results if r["posting_id"] == posting_id]
    assert result["location"] is None and result["budget"] is None and result["availability"] is None
    components = result["rule_components"]
    assert components["location"] is None and components["budget_fit"] is None and components["availability"] is None
    assert components["skill_overlap"] == 1.0
