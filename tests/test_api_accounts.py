"""Accounts, sessions and access guards through the API, against a real schema (skipped without DATABASE_URL)."""

import pytest

from kaziforce_api.app import create_app
from kaziforce_api.data.accounts import AccountStore
from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.seed import seed, skill_rows
from kaziforce_api.data.store import PostgresProfileStore
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_api.service import RecommendationService
from tests.conftest import requires_db

pytestmark = [pytest.mark.db, requires_db]

PIN = "4821"
PROFILE = {"biography": "Mimi ni fundi wa umeme, nina uzoefu wa miaka mitano. Niko Nyeri.",
           "skills": ["fundi wa umeme"], "location": "Nyeri", "availability": "Part-time",
           "rate_expectation": 2000}
JOB = {"title": "Rewire a small shop", "description": "We need an electrician in Nyeri to rewire a small shop.",
       "required_skills": ["install electricity sockets"], "location": "Nyeri", "budget": 2600}


@pytest.fixture(scope="module")
def app(pg_connect, stub_encoder):
    loader = DataLoader()
    workers, jobs = loader.workers("development"), loader.jobs()
    conn = pg_connect()
    seed(conn, workers, jobs, skill_rows(workers, jobs))
    conn.close()
    service = RecommendationService(PostgresProfileStore(pg_connect),
                                    semantic_factory=lambda: SemanticScorer(encoder=stub_encoder))
    return create_app(service.start(background=False), accounts=AccountStore(pg_connect))


@pytest.fixture
def client(app):
    return app.test_client()


_next_number = iter(range(700_000_000, 700_001_000))


def phone() -> str:
    return str(next(_next_number))


def register(client, role: str, pin: str = PIN) -> str:
    number = phone()
    created = client.post("/auth/accounts", json={"phone": number, "pin": pin, "role": role})
    assert created.status_code == 201, created.get_json()
    return number


# Creating an account and signing in

def test_creating_an_account_signs_you_in_and_says_what_you_own(client):
    number = phone()
    created = client.post("/auth/accounts", json={"phone": number, "pin": PIN, "role": "worker"})
    assert created.status_code == 201
    assert created.get_json() == {"account": {"account_id": pytest.approx(created.get_json()["account"]["account_id"]),
                                              "phone": number, "role": "worker"},
                                  "worker_profile_id": None, "postings": 0}
    cookie = created.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and PIN not in cookie
    assert client.get("/auth/session").get_json()["account"]["role"] == "worker"


def test_the_pin_never_comes_back_in_any_response(client):
    number = phone()
    created = client.post("/auth/accounts", json={"phone": number, "pin": PIN, "role": "client"})
    for response in (created, client.get("/auth/session")):
        assert PIN not in response.get_data(as_text=True)
        assert PIN not in str(dict(response.headers))


@pytest.mark.parametrize("typed", ["0712345679", "+254 712 345 679", "254712345679"])
def test_one_number_written_three_ways_is_one_account(client, typed):
    client.post("/auth/accounts", json={"phone": "712345679", "pin": PIN, "role": "worker"})
    again = client.post("/auth/accounts", json={"phone": typed, "pin": PIN, "role": "worker"})
    assert again.status_code == 409 and again.get_json()["error"]["code"] == "already_exists"


def test_signing_in_needs_the_right_pin(client):
    number = register(client, "worker")
    client.delete("/auth/sessions")
    assert client.post("/auth/sessions", json={"phone": number, "pin": "0000"}).status_code == 401
    ok = client.post("/auth/sessions", json={"phone": number, "pin": PIN})
    assert ok.status_code == 200 and ok.get_json()["account"]["phone"] == number


def test_an_unknown_number_and_a_wrong_pin_look_the_same(client):
    number = register(client, "worker")
    unknown = client.post("/auth/sessions", json={"phone": "799999999", "pin": PIN})
    wrong = client.post("/auth/sessions", json={"phone": number, "pin": "0000"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json() == wrong.get_json()


def test_repeated_wrong_pins_lock_the_account(client):
    number = register(client, "worker")
    for _ in range(5):
        client.post("/auth/sessions", json={"phone": number, "pin": "0000"})
    locked = client.post("/auth/sessions", json={"phone": number, "pin": PIN})  # even the right PIN
    assert locked.status_code == 423 and locked.get_json()["error"]["code"] == "locked"


def test_signing_out_ends_the_session(client):
    register(client, "client")
    assert client.delete("/auth/sessions").status_code == 200
    assert client.get("/auth/session").status_code == 401


@pytest.mark.parametrize("body, field", [
    ({"phone": "712345678", "pin": "12", "role": "worker"}, "pin"),
    ({"phone": "abc", "pin": PIN, "role": "worker"}, "phone"),
    ({"phone": "712345678", "pin": PIN, "role": "admin"}, "role"),
    ({"phone": "712345678", "pin": PIN}, "role"),
])
def test_bad_credentials_are_refused_with_the_field(client, body, field):
    response = client.post("/auth/accounts", json=body)
    assert response.status_code == 400 and response.get_json()["error"]["field"] == field


# The worker journey

def test_a_worker_creates_one_profile_and_gets_their_own_matches(client):
    register(client, "worker")
    created = client.post("/workers", json=PROFILE)
    assert created.status_code == 201
    worker_id = created.get_json()["worker_id"]
    assert client.get("/auth/session").get_json()["worker_profile_id"] == worker_id

    mine = client.get("/workers/me").get_json()
    assert mine["worker_id"] == worker_id and mine["worker"]["location"] == "Nyeri"

    # No worker_id needed: the signed-in worker asks for their own matches.
    matches = client.post("/recommend", json={"k": 10})
    assert matches.status_code == 200
    body = matches.get_json()
    assert body["worker"]["worker_id"] == worker_id and body["display_threshold"] == 55
    assert all(r["match_score"] == round(r["scores"]["composite"] * 100) for r in body["results"])
    assert all(r["band"] in ("strong", "moderate", "weak", "below_threshold") for r in body["results"])


def test_a_second_profile_is_refused(client):
    register(client, "worker")
    assert client.post("/workers", json=PROFILE).status_code == 201
    again = client.post("/workers", json=PROFILE)
    assert again.status_code == 409 and again.get_json()["error"]["code"] == "already_exists"


def test_a_worker_without_a_profile_is_told_to_create_one(client):
    register(client, "worker")
    assert client.get("/workers/me").status_code == 404
    assert client.post("/recommend", json={"k": 5}).status_code == 403


# The client journey

def test_a_client_posts_jobs_and_sees_only_their_own(client, app):
    register(client, "client")
    first = client.post("/jobs", json=JOB).get_json()["posting_id"]
    second = client.post("/jobs", json={**JOB, "title": "Fix a socket"}).get_json()["posting_id"]

    listed = client.get("/jobs")
    assert listed.status_code == 200
    postings = listed.get_json()["postings"]
    assert {p["posting_id"] for p in postings} == {first, second}
    assert [t["label"] for t in postings[0]["trades"]] == ["electrician"]

    other = app.test_client()
    register(other, "client")
    assert other.get("/jobs").get_json()["postings"] == []
    # A client cannot open someone else's posting.
    assert other.get(f"/jobs/{first}").status_code == 404


def test_the_trade_list_shows_no_identifiers_scores_or_ranking(client):
    register(client, "client")
    interpretation = client.post("/jobs", json=JOB).get_json()["interpretation"]
    (pool,) = [p for p in interpretation["worker_pool"] if p["occupation"]["label"] == "electrician"]
    assert pool["workers"] > 0 and 1 <= len(pool["sample"]) <= 5
    for worker in pool["sample"]:
        assert set(worker) == {"describes_as", "location", "availability", "rate_expectation"}
    text = str(interpretation)
    assert "worker_id" not in text and "composite" not in text and "rank" not in text


# Guards between the two roles

def test_a_client_cannot_use_worker_endpoints(client):
    register(client, "client")
    assert client.get("/workers/me").status_code == 403
    assert client.post("/workers", json=PROFILE).status_code == 403


def test_a_worker_cannot_post_or_list_jobs(client):
    register(client, "worker")
    assert client.post("/jobs", json=JOB).status_code == 403
    assert client.get("/jobs").status_code == 403


def test_signed_out_visitors_are_asked_to_sign_in(client):
    for call in (lambda: client.get("/auth/session"), lambda: client.get("/workers/me"), lambda: client.get("/jobs")):
        response = call()
        assert response.status_code == 401 and response.get_json()["error"]["code"] == "unauthenticated"
