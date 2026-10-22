"""POST /recommend and GET /health: the contract in docs/api.md, with a stub encoder (no model in CI)."""

import numpy as np
import pytest

from kaziforce_api.app import create_app
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_api.data.store import CsvProfileStore
from kaziforce_api.service import RecommendationService

EXAMPLE = "3917d39f-d0c0-46c2-aa34-9158711f68f3"  # development known_alias worker, fundi wa umeme
TYPED = {"biography": "Mimi ni fundi bomba, niko Kisumu.", "skills": ["fundi bomba"], "location": "Kisumu",
         "availability": None, "rate_expectation": None}


def _letters(texts):
    return np.array([[t.lower().count(c) for c in "abcdefghijklmnopqrstuvwxyz"] for t in texts], dtype=float) + 1e-3


@pytest.fixture(scope="module")
def service():
    return RecommendationService(CsvProfileStore(), semantic_factory=lambda: SemanticScorer(encoder=_letters)).start(background=False)


@pytest.fixture()
def client(service):
    return create_app(service).test_client()


def post(client, body, **kw):
    return client.post("/recommend", json=body, **kw)


# Success

def test_health_reports_readiness_and_pool_size(client):
    assert client.get("/health").get_json() == {"status": "ok", "ready": True, "candidate_jobs": 280}
    not_started = create_app(RecommendationService(CsvProfileStore()), start=False).test_client()
    assert not_started.get("/health").get_json() == {"status": "ok", "ready": False, "candidate_jobs": 0}


def test_stored_worker_returns_the_contract_shape(client):
    r = post(client, {"worker_id": EXAMPLE, "k": 3})
    assert r.status_code == 200
    d = r.get_json()
    assert list(d) == ["configuration", "k", "worker", "enrichment", "results", "display_threshold", "timing_ms"]
    assert (d["configuration"], d["k"], d["worker"]["worker_id"]) == ("full", 3, EXAMPLE)
    assert d["enrichment"]["terms"] == [{"id": "term:fundi umeme", "label": "fundi wa umeme"}]
    assert [o["label"] for o in d["enrichment"]["occupations"]] == ["electrician"]
    assert [x["rank"] for x in d["results"]] == [1, 2, 3]
    top = d["results"][0]
    assert set(top) == {"rank", "posting_id", "title", "description", "location", "availability", "budget", "scores",
                        "match_score", "band", "rule_components", "matched_skills"}
    assert set(top["scores"]) == {"composite", "rule", "semantic"}
    assert set(top["rule_components"]) == {"skill_overlap", "location", "budget_fit", "availability"}
    skill = top["matched_skills"][0]
    assert skill["source"] == "informal_term" and len(skill["graph_path"]) == 2
    first, second = skill["graph_path"]
    assert first["relation"] == "MAPS_TO" and first["source"] == {"id": "term:fundi umeme", "label": "fundi wa umeme",
                                                                   "type": "InformalTerm"}
    assert first["target"]["type"] == "Occupation" and second["relation"] == "HAS_ESSENTIAL_SKILL"
    assert second["target"] == {"id": skill["skill"], "label": skill["skill_label"], "type": "Skill"}


def test_typed_in_profile_has_no_worker_id_and_absent_criteria_are_null(client):
    d = post(client, {"worker": TYPED, "k": 50}).get_json()
    assert d["worker"]["worker_id"] is None and d["worker"]["availability"] is None
    assert [o["label"] for o in d["enrichment"]["occupations"]] == ["plumber"]
    assert len(d["results"]) == 50
    for x in d["results"]:
        c = x["rule_components"]
        assert c["availability"] is None and c["budget_fit"] is None  # worker gave neither: null, never 0
        assert isinstance(c["skill_overlap"], float)


def test_unused_components_are_null_not_zero(client):
    for configuration, rule_used, semantic_used in [("keyword", False, False), ("rule_only", True, False),
                                                    ("semantic_kg", False, True), ("hybrid_no_kg", True, True)]:
        d = post(client, {"worker_id": EXAMPLE, "configuration": configuration, "k": 50}).get_json()
        for x in d["results"]:
            assert (x["scores"]["rule"] is not None) == rule_used, configuration
            assert (x["scores"]["semantic"] is not None) == semantic_used, configuration
            assert (x["rule_components"] is not None) == rule_used, configuration
            assert x["scores"]["composite"] is not None


def test_distractor_postings_have_null_fields_and_null_criteria(client):
    office = {"biography": "Office administrator", "skills": ["communication", "problem solving", "teamwork"]}
    d = post(client, {"worker": office, "k": 10, "configuration": "rule_only"}).get_json()
    distractors = [x for x in d["results"] if x["budget"] is None]
    assert distractors, "expected Job Skill Set postings to rank first for an office profile"
    for x in distractors:
        assert x["location"] is None and x["availability"] is None
        assert x["rule_components"]["location"] is None and x["rule_components"]["budget_fit"] is None


# Errors

@pytest.mark.parametrize("body, field", [
    ({}, None), ({"worker_id": EXAMPLE, "worker": TYPED}, None), ({"worker_id": ""}, "worker_id"),
    ({"worker_id": 7}, "worker_id"), ({"worker_id": EXAMPLE, "k": 0}, "k"), ({"worker_id": EXAMPLE, "k": 51}, "k"),
    ({"worker_id": EXAMPLE, "k": "5"}, "k"), ({"worker_id": EXAMPLE, "k": True}, "k"),
    ({"worker_id": EXAMPLE, "configuration": "bm25"}, "configuration"), ({"worker_id": EXAMPLE, "extra": 1}, None),
    ({"worker": {**TYPED, "biography": "  "}}, "worker.biography"), ({"worker": {**TYPED, "skills": "fundi"}}, "worker.skills"),
    ({"worker": {**TYPED, "availability": "Sometimes"}}, "worker.availability"),
    ({"worker": {**TYPED, "rate_expectation": -1}}, "worker.rate_expectation"),
    ({"worker": {**TYPED, "rate_expectation": True}}, "worker.rate_expectation"),
    ({"worker": {**TYPED, "name": "x"}}, "worker"), ({"worker": "fundi"}, "worker"),
])
def test_invalid_requests_are_400_with_the_field(client, body, field):
    r = post(client, body)
    assert r.status_code == 400
    err = r.get_json()["error"]
    assert err["code"] == "invalid_request" and err["message"] and err.get("field") == field


def test_malformed_json_and_non_object_bodies_are_400(client):
    for data in ("{not json", "[1, 2]", ""):
        r = client.post("/recommend", data=data, content_type="application/json")
        assert r.status_code == 400 and r.get_json()["error"]["code"] == "invalid_request"


def test_unknown_or_other_split_worker_is_404(client):
    from kaziforce_api.data.data_loader import DataLoader
    test_split_worker = DataLoader().workers("test")[0].worker_id
    for worker_id in ("no-such-worker", test_split_worker):
        r = post(client, {"worker_id": worker_id})
        assert r.status_code == 404 and r.get_json()["error"] == {
            "code": "not_found", "message": f"no stored worker with id {worker_id}", "field": "worker_id"}


def test_not_ready_is_503_with_retry_after():
    client = create_app(RecommendationService(CsvProfileStore()), start=False).test_client()
    r = post(client, {"worker": TYPED})
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "not_ready" and r.headers["Retry-After"] == "5"


def test_unexpected_errors_are_500_without_a_trace(service, monkeypatch):
    client = create_app(service).test_client()
    monkeypatch.setattr(service, "recommend", lambda *a, **k: (_ for _ in ()).throw(ZeroDivisionError("boom")))
    r = post(client, {"worker": TYPED})
    assert r.status_code == 500 and r.get_json() == {"error": {"code": "internal_error", "message": "internal server error"}}
    assert "boom" not in r.get_data(as_text=True) and "Traceback" not in r.get_data(as_text=True)


def test_unknown_route_and_wrong_method_are_json(client):
    assert client.get("/nope").status_code == 404 and client.get("/nope").get_json()["error"]["code"] == "not_found"
    r = client.get("/recommend")
    assert r.status_code == 405 and r.get_json()["error"]["code"] == "method_not_allowed"


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_cors_allows_each_spelling_of_the_web_app_origin(client, origin):
    ok = client.options("/recommend", headers={"Origin": origin})
    assert ok.status_code == 204 and ok.headers["Access-Control-Allow-Origin"] == origin
    allowed = post(client, {"worker": TYPED}, headers={"Origin": origin})
    assert allowed.headers["Access-Control-Allow-Origin"] == origin


def test_cors_refuses_any_other_origin(client):
    for origin in ("http://evil.example", "http://localhost:3001"):
        other = post(client, {"worker": TYPED}, headers={"Origin": origin})
        assert "Access-Control-Allow-Origin" not in other.headers


def test_cors_origins_can_be_configured(monkeypatch, service):
    monkeypatch.setenv("KAZIFORCE_CORS_ORIGIN", "https://example.test , http://localhost:4000")
    configured = create_app(service).test_client()
    for origin in ("https://example.test", "http://localhost:4000"):
        response = configured.options("/recommend", headers={"Origin": origin})
        assert response.headers["Access-Control-Allow-Origin"] == origin
    assert "Access-Control-Allow-Origin" not in configured.options(
        "/recommend", headers={"Origin": "http://localhost:3000"}
    ).headers


# POST /workers and POST /jobs: validation and the read-only store (storage itself is tested in test_api_db.py)

JOB = {"title": "House wiring for a new flat", "description": "Need an electrician to wire a new flat in Nyeri.",
       "required_skills": ["install electricity sockets"], "location": "Nyeri", "budget": 2500}


@pytest.mark.parametrize("path, body, field", [
    ("/workers", {"biography": "  "}, "worker.biography"),
    ("/workers", {}, "worker.biography"),
    ("/workers", {"biography": "x", "availability": "Sometimes"}, "worker.availability"),
    ("/workers", {"biography": "x", "rate_expectation": -5}, "worker.rate_expectation"),
    ("/workers", {"biography": "x", "skills": "fundi"}, "worker.skills"),
    ("/workers", {"biography": "x", "worker_id": "abc"}, "worker"),
    ("/workers", "not an object", "worker"),
    ("/jobs", {**JOB, "title": ""}, "title"),
    ("/jobs", {k: v for k, v in JOB.items() if k != "description"}, "description"),
    ("/jobs", {**JOB, "budget": "2500"}, "budget"),
    ("/jobs", {**JOB, "required_skills": [1, 2]}, "required_skills"),
    ("/jobs", {**JOB, "availability": "Evenings"}, "availability"),
    ("/jobs", {**JOB, "category": "Electrician"}, None),
    ("/jobs", {**JOB, "title": "x" * 256}, "title"),
])
def test_profile_submission_validation(client, path, body, field):
    r = client.post(path, json=body)
    assert r.status_code == 400, r.get_json()
    err = r.get_json()["error"]
    assert err["code"] == "invalid_request" and err.get("field") == field


def test_category_is_rejected_because_matching_never_uses_it(client):
    r = client.post("/jobs", json={**JOB, "category": "Electrician"})
    assert r.status_code == 400 and "category" in r.get_json()["error"]["message"]


def test_storing_is_refused_when_the_store_is_read_only(client):
    for path, body in (("/workers", {"biography": "Mimi ni fundi bomba"}), ("/jobs", JOB)):
        r = client.post(path, json=body)
        assert r.status_code == 501
        assert r.get_json()["error"] == {"code": "not_supported",
                                         "message": "this server cannot store new profiles "
                                                    "(it is reading the frozen dataset, not a database)"}


def test_job_interpretation_shows_stated_skills_only(client):
    posting_id = "979d6da3-3b29-43cd-8e3f-8e612197d124"  # synthetic electrician posting
    d = client.get(f"/jobs/{posting_id}").get_json()
    assert d["posting_id"] == posting_id and d["candidate_jobs"] == 280
    assert d["job"]["title"] == "Electrical fault-finding in an office"
    interpretation = d["interpretation"]
    assert [o["label"] for o in interpretation["occupations"]] == ["electrician"]
    stated = interpretation["stated_skills"]
    assert [s["skill_label"] for s in stated] == list(d["job"]["required_skills"])
    assert all(s["source"] in ("listed", "text") for s in stated)
    # the posting states 4 skills; its occupation would infer 21 essential ones, which are not reported
    assert len(stated) == len(d["job"]["required_skills"]) == 4
    assert [p["occupation"]["label"] for p in interpretation["worker_pool"]] == ["electrician"]


def test_unknown_or_malformed_posting_is_404(client):
    for posting_id in ("not-a-uuid", "11111111-1111-4111-8111-111111111111"):
        r = client.get(f"/jobs/{posting_id}")
        assert r.status_code == 404 and r.get_json()["error"]["field"] == "posting_id"
