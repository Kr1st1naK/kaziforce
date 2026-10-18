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

def test_health_reports_readiness(client):
    assert client.get("/health").get_json() == {"status": "ok", "ready": True}
    not_started = create_app(RecommendationService(CsvProfileStore()), start=False).test_client()
    assert not_started.get("/health").get_json() == {"status": "ok", "ready": False}


def test_stored_worker_returns_the_contract_shape(client):
    r = post(client, {"worker_id": EXAMPLE, "k": 3})
    assert r.status_code == 200
    d = r.get_json()
    assert list(d) == ["configuration", "k", "worker", "enrichment", "results", "timing_ms"]
    assert (d["configuration"], d["k"], d["worker"]["worker_id"]) == ("full", 3, EXAMPLE)
    assert d["enrichment"]["terms"] == [{"id": "term:fundi umeme", "label": "fundi wa umeme"}]
    assert [o["label"] for o in d["enrichment"]["occupations"]] == ["electrician"]
    assert [x["rank"] for x in d["results"]] == [1, 2, 3]
    top = d["results"][0]
    assert set(top) == {"rank", "posting_id", "title", "description", "location", "availability", "budget", "scores",
                        "rule_components", "matched_skills"}
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


def test_cors_for_the_web_app_origin_only(client):
    ok = client.options("/recommend", headers={"Origin": "http://localhost:3000"})
    assert ok.status_code == 204 and ok.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    other = post(client, {"worker": TYPED}, headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in other.headers
