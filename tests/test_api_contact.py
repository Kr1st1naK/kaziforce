"""
Names, consent and the client's view of a worker, through the API against a real schema.

A worker gives a name and agrees at sign-up; only a worker who has done so, and not withdrawn,
can be opened by a client, and only by a signed-in client, slowly. Nothing personal may be stored
in the clear, logged, or returned to anyone it was not meant for.
"""

import itertools
import logging

import pytest

from kaziforce_api.app import create_app
from kaziforce_api.crypto import ConfigError
from kaziforce_api.data.accounts import AccountStore
from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.models import WorkerProfile
from kaziforce_api.data.seed import seed, skill_rows
from kaziforce_api.data.store import PostgresProfileStore
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_api.ratelimit import SlidingWindowLimiter
from kaziforce_api.service import TRADE_SAMPLE_SIZE, RecommendationService
from tests.conftest import requires_db

pytestmark = [pytest.mark.db, requires_db]

PIN = "4821"
JOB = {"title": "Rewire a small shop", "description": "We need an electrician in Nyeri to rewire a small shop.",
       "required_skills": ["install electricity sockets"], "location": "Nyeri", "budget": 2600}
PROFILE = {"biography": "Mimi ni fundi wa umeme, nina uzoefu wa miaka mitano. Niko Nyeri.",
           "skills": ["fundi wa umeme"], "location": "Nyeri", "availability": "Part-time", "rate_expectation": 2000}


@pytest.fixture(scope="module")
def app(pg_connect, stub_encoder, crypto):
    loader = DataLoader()
    workers, jobs = loader.workers("development"), loader.jobs()
    conn = pg_connect()
    seed(conn, workers, jobs, skill_rows(workers, jobs))
    conn.close()
    service = RecommendationService(PostgresProfileStore(pg_connect),
                                    semantic_factory=lambda: SemanticScorer(encoder=stub_encoder))
    return create_app(service.start(background=False), accounts=AccountStore(pg_connect, crypto))


@pytest.fixture
def stores(app):
    return app.extensions["kaziforce"], app.extensions["kaziforce_accounts"]


_numbers = itertools.count(700_300_000)
# Descending, so each new worker sorts ahead of the last and is always in the trade's sample
# (the sample is the first few by worker_id; see TRADE_SAMPLE_SIZE).
_ids = itertools.count(999_000, -1)


def phone() -> str:
    return str(next(_numbers))


def sign_up(client, role="worker", first="Amina", last="Wanjiru", **over):
    number = phone()
    body = {"phone": number, "pin": PIN, "role": role}
    if role == "worker":
        body |= {"first_name": first, "last_name": last, "contact_consent": True}
    response = client.post("/auth/accounts", json=body | over)
    return number, response


def named_worker(app, stores, **kw):
    """A signed-up worker with a profile that sorts first in its trade. Returns (client, phone, worker_id)."""
    service, accounts = stores
    client = app.test_client()
    number, created = sign_up(client, **kw)
    assert created.status_code == 201, created.get_json()
    account_id = created.get_json()["account"]["account_id"]
    worker_id = f"00000000-0000-4000-8000-{next(_ids):012d}"
    stored = service.create_worker(WorkerProfile(worker_id, PROFILE["biography"], tuple(PROFILE["skills"]),
                                                 PROFILE["location"], PROFILE["availability"], 2000.0))
    accounts.claim_worker_profile(account_id, stored["worker_id"])
    return client, number, stored["worker_id"]


def client_account(app):
    client = app.test_client()
    number, created = sign_up(client, role="client")
    assert created.status_code == 201, created.get_json()
    return client, number


def trade_sample(client):
    posted = client.post("/jobs", json=JOB)
    assert posted.status_code == 201, posted.get_json()
    pool = posted.get_json()["interpretation"]["worker_pool"][0]
    return pool, pool["sample"]


def public_id_of(app, stores, **kw):
    worker_client, number, worker_id = named_worker(app, stores, **kw)
    viewer, _ = client_account(app)
    _, sample = trade_sample(viewer)
    return worker_client, viewer, number, next(c["public_id"] for c in sample if "public_id" in c)


# Sign-up

def test_a_worker_signs_up_with_a_name_and_agreement(app):
    number, created = sign_up(app.test_client())
    assert created.status_code == 201
    assert "Amina" not in created.get_data(as_text=True)


@pytest.mark.parametrize("field", ["first_name", "last_name"])
@pytest.mark.parametrize("bad", [None, "", "   ", "x" * 61, "A1", "<b>", "Amina;DROP", 12, ["A"], "-", "'"])
def test_a_name_must_be_present_trimmed_and_sensible(app, field, bad):
    _, response = sign_up(app.test_client(), **{field: bad})
    assert response.status_code == 400 and response.get_json()["error"]["field"] == field


@pytest.mark.parametrize("good,stored", [("  Amina  ", "Amina"), ("Mary-Anne", "Mary-Anne"), ("O'Neil", "O'Neil"),
                                         ("Wanjiru  Njoroge", "Wanjiru Njoroge"), ("Zoë", "Zoë"), ("A", "A")])
def test_a_reasonable_name_is_accepted_and_tidied(app, good, stored):
    client = app.test_client()
    _, response = sign_up(client, first=good)
    assert response.status_code == 201
    assert client.post("/workers", json=PROFILE).status_code == 201  # a profile, so /workers/me answers
    assert client.get("/workers/me").get_json()["contact"]["first_name"] == stored


@pytest.mark.parametrize("consent", [None, False, "true", 1, "yes"])
def test_a_worker_must_agree_to_be_shown(app, consent):
    _, response = sign_up(app.test_client(), contact_consent=consent)
    assert response.status_code == 400 and response.get_json()["error"]["field"] == "contact_consent"


@pytest.mark.parametrize("field,value", [("first_name", "Peter"), ("last_name", "Kamau"), ("contact_consent", True)])
def test_a_client_gives_no_name_and_no_consent(app, field, value):
    _, response = sign_up(app.test_client(), role="client", **{field: value})
    assert response.status_code == 400 and response.get_json()["error"]["field"] == field


def test_a_client_signs_up_as_before(app):
    assert sign_up(app.test_client(), role="client")[1].status_code == 201


def test_sign_in_takes_no_name_fields(app):
    number, _ = sign_up(app.test_client())
    response = app.test_client().post("/auth/sessions", json={"phone": number, "pin": PIN, "first_name": "Amina"})
    assert response.status_code == 400


# Nothing personal is stored in the clear

def test_no_phone_or_name_is_stored_in_the_clear(app, pg_connect):
    number, _ = sign_up(app.test_client(), first="Zuberi", last="Mwangangi")
    conn = pg_connect()
    with conn.cursor() as cur:
        cur.execute("SELECT row_to_json(a)::text FROM account a")
        dump = " ".join(r[0] for r in cur.fetchall())
        cur.execute("SELECT phone_enc, first_name_enc, last_name_enc, phone_hash FROM account")
        rows = cur.fetchall()
    conn.close()
    for secret in (number, number[3:], "Zuberi", "Mwangangi", PIN):
        assert secret not in dump
    assert rows and all(r[0].startswith("v1:") for r in rows)
    assert all(r[1] is None or r[1].startswith("v1:") for r in rows)
    assert all(len(r[3]) == 64 for r in rows)


def test_the_same_names_are_stored_differently_each_time(app, pg_connect):
    sign_up(app.test_client(), first="Rehema", last="Otieno")
    sign_up(app.test_client(), first="Rehema", last="Otieno")
    conn = pg_connect()
    with conn.cursor() as cur:
        cur.execute("SELECT count(DISTINCT first_name_enc), count(*) FROM account WHERE first_name_enc IS NOT NULL")
        distinct, total = cur.fetchone()
    conn.close()
    assert distinct == total


def test_sign_in_still_works_through_the_hash(app):
    number, _ = sign_up(app.test_client())
    assert app.test_client().post("/auth/sessions", json={"phone": number, "pin": PIN}).status_code == 200
    # every spelling of the number reaches the same account
    assert app.test_client().post("/auth/sessions", json={"phone": f"0{number}", "pin": PIN}).status_code == 200
    assert app.test_client().post("/auth/sessions", json={"phone": number, "pin": "0000"}).status_code == 401


def test_a_duplicate_number_is_refused_whatever_its_spelling(app):
    number, _ = sign_up(app.test_client())
    again = app.test_client().post("/auth/accounts", json={"phone": f"+254{number}", "pin": PIN, "role": "client"})
    assert again.status_code == 409


def test_a_worker_reads_their_own_name_and_number(app, stores):
    worker, number, _ = named_worker(app, stores, first="Amina", last="Wanjiru")
    contact = worker.get("/workers/me").get_json()["contact"]
    assert contact == {"first_name": "Amina", "last_name": "Wanjiru", "consent": True, "phone": number}


# The client's view of a worker

def test_a_card_shows_a_consenting_workers_name_and_a_link_target(app, stores):
    _, viewer, _, public_id = public_id_of(app, stores)
    _, sample = trade_sample(viewer)
    named = [c for c in sample if "public_id" in c]
    assert named and named[0]["name"] == "Amina Wanjiru" and named[0]["public_id"] == public_id
    assert all(("public_id" in c) == ("name" in c) for c in sample)  # an anonymous card has neither


def test_a_clients_view_of_a_worker_has_the_profile_and_the_number(app, stores):
    _, viewer, number, public_id = public_id_of(app, stores, first="Amina", last="Wanjiru")
    response = viewer.get(f"/workers/{public_id}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["first_name"] == "Amina" and body["last_name"] == "Wanjiru"
    assert body["trade"] and body["location"] == "Nyeri" and body["availability"] == "Part-time"
    assert body["rate_expectation"] == 2000 and body["skills"] == ["fundi wa umeme"] and body["biography"]
    assert body["contact"] == {"phone_e164": f"+254{number}", "phone_local": number}


def test_a_clients_view_leaks_no_identifier_or_secret(app, stores):
    _, viewer, number, public_id = public_id_of(app, stores)
    response = viewer.get(f"/workers/{public_id}")
    assert set(response.get_json()) == {"public_id", "first_name", "last_name", "trade", "skills", "biography",
                                        "location", "availability", "rate_expectation", "contact"}
    for forbidden in ("worker_id", "account_id", "pin", "hash", "consent", "salt"):
        assert forbidden not in response.get_data(as_text=True).lower()


def test_the_internal_worker_id_never_reaches_a_client(app, stores):
    _, _, worker_id = named_worker(app, stores)
    viewer, _ = client_account(app)
    assert worker_id not in viewer.post("/jobs", json=JOB).get_data(as_text=True)


def test_withdrawing_consent_hides_the_profile_at_once(app, stores):
    worker, viewer, _, public_id = public_id_of(app, stores)
    assert viewer.get(f"/workers/{public_id}").status_code == 200

    off = worker.put("/workers/me", json={**PROFILE, "contact_consent": False})
    assert off.status_code == 200 and off.get_json()["contact"]["consent"] is False
    assert viewer.get(f"/workers/{public_id}").status_code == 404
    _, sample = trade_sample(viewer)
    assert public_id not in str(sample)  # other workers in the trade may share the name; this one's id is gone

    assert worker.put("/workers/me", json={**PROFILE, "contact_consent": True}).status_code == 200
    assert viewer.get(f"/workers/{public_id}").status_code == 200


def test_a_withdrawn_worker_looks_exactly_like_one_that_does_not_exist(app, stores):
    worker, viewer, _, public_id = public_id_of(app, stores)
    worker.put("/workers/me", json={**PROFILE, "contact_consent": False})
    hidden = viewer.get(f"/workers/{public_id}")
    unknown = viewer.get("/workers/00000000-0000-4000-8000-00000000dead")
    malformed = viewer.get("/workers/not-an-id")
    assert hidden.status_code == unknown.status_code == malformed.status_code == 404
    assert hidden.get_json() == unknown.get_json() == malformed.get_json()
    assert public_id not in hidden.get_data(as_text=True)


def test_consent_does_not_change_the_sample_or_the_count(app, stores):
    worker, viewer, _, _ = public_id_of(app, stores)
    with_consent, sample_on = trade_sample(viewer)
    worker.put("/workers/me", json={**PROFILE, "contact_consent": False})
    without, sample_off = trade_sample(viewer)
    assert with_consent["workers"] == without["workers"]
    assert len(sample_on) == len(sample_off) == TRADE_SAMPLE_SIZE

    def plain(cards):
        return [{k: v for k, v in c.items() if k not in ("public_id", "name")} for c in cards]

    assert plain(sample_on) == plain(sample_off)


def test_a_worker_with_no_name_stays_anonymous_whatever_their_consent(app, stores, pg_connect):
    """An account from before names existed: no name, so nothing to show, and consent cannot be on."""
    service, accounts = stores
    worker = app.test_client()
    _, created = sign_up(worker, first="Old", last="Account")
    account_id = created.get_json()["account"]["account_id"]
    conn = pg_connect()
    with conn, conn.cursor() as cur:  # the state an existing account is in after the migration
        cur.execute("UPDATE account SET first_name_enc = NULL, last_name_enc = NULL, contact_consent = FALSE "
                    "WHERE account_id = %s", (account_id,))
    conn.close()
    stored = service.create_worker(WorkerProfile(f"00000000-0000-4000-8000-{next(_ids):012d}", PROFILE["biography"],
                                                 tuple(PROFILE["skills"]), "Nyeri", "Part-time", 2000.0))
    accounts.claim_worker_profile(account_id, stored["worker_id"])
    contact = worker.get("/workers/me").get_json()["contact"]
    assert contact["first_name"] is None and contact["consent"] is False

    viewer, _ = client_account(app)
    _, sample = trade_sample(viewer)
    assert not any(c.get("name") == "Old Account" for c in sample)
    assert all("public_id" not in c for c in sample if c["describes_as"] == "fundi wa umeme" and "name" not in c)
    refused = worker.put("/workers/me", json={**PROFILE, "contact_consent": True})
    assert refused.status_code == 400 and refused.get_json()["error"]["field"] == "contact_consent"
    added = worker.put("/workers/me", json={**PROFILE, "first_name": "Now", "last_name": "Named",
                                            "contact_consent": True})
    assert added.status_code == 200 and added.get_json()["contact"]["first_name"] == "Now"


def test_a_name_can_be_edited_and_one_half_cannot_be_set_alone(app, stores):
    worker, _, _ = named_worker(app, stores)
    edited = worker.put("/workers/me", json={**PROFILE, "first_name": "Aminata", "last_name": "Kamau"})
    assert edited.status_code == 200
    assert worker.get("/workers/me").get_json()["contact"]["first_name"] == "Aminata"
    # left out, name and consent stay as they were
    assert worker.put("/workers/me", json=PROFILE).status_code == 200
    kept = worker.get("/workers/me").get_json()["contact"]
    assert kept["first_name"] == "Aminata" and kept["consent"] is True
    bad = worker.put("/workers/me", json={**PROFILE, "first_name": "  "})
    assert bad.status_code == 400 and bad.get_json()["error"]["field"] == "first_name"
    assert worker.put("/workers/me", json={**PROFILE, "contact_consent": "no"}).status_code == 400


# Who may ask

def test_an_unauthenticated_request_for_a_worker_is_refused(app, stores):
    _, _, _, public_id = public_id_of(app, stores)
    response = app.test_client().get(f"/workers/{public_id}")
    assert response.status_code == 401 and "Amina" not in response.get_data(as_text=True)


def test_a_worker_cannot_open_a_workers_profile(app, stores):
    owner, _, _, public_id = public_id_of(app, stores)
    other, _, _ = named_worker(app, stores, first="Other", last="Worker")
    for who in (other, owner):  # another worker, and the worker themselves
        response = who.get(f"/workers/{public_id}")
        assert response.status_code == 403
        assert "Amina" not in response.get_data(as_text=True)


def test_recommend_never_carries_a_name_or_a_phone(app, stores):
    worker, number, worker_id = named_worker(app, stores, first="Zuberi", last="Mwangangi")
    bodies = (app.test_client().post("/recommend", json={"worker_id": worker_id}).get_data(as_text=True),
              worker.post("/recommend", json={}).get_data(as_text=True))
    for body in bodies:
        assert "Zuberi" not in body and "Mwangangi" not in body and number not in body


# Slowing bulk collection

def limited_app(stores, limit, clock):
    service, accounts = stores
    return create_app(service, accounts=accounts, contact_limiter=SlidingWindowLimiter(limit, 60, clock=clock))


def test_profile_views_are_rate_limited_per_client(app, stores):
    _, _, _, public_id = public_id_of(app, stores)
    now = [1000.0]
    limited = limited_app(stores, 3, lambda: now[0])
    viewer = limited.test_client()
    assert sign_up(viewer, role="client")[1].status_code == 201

    assert [viewer.get(f"/workers/{public_id}").status_code for _ in range(3)] == [200, 200, 200]
    refused = viewer.get(f"/workers/{public_id}")
    assert refused.status_code == 429 and refused.get_json()["error"]["code"] == "rate_limited"
    assert int(refused.headers["Retry-After"]) >= 1
    assert "Amina" not in refused.get_data(as_text=True)

    other = limited.test_client()  # another client is not held back by it
    sign_up(other, role="client")
    assert other.get(f"/workers/{public_id}").status_code == 200

    now[0] += 61  # the window passes
    assert viewer.get(f"/workers/{public_id}").status_code == 200


def test_guessing_ids_uses_up_the_same_allowance(stores):
    now = [1000.0]
    viewer = limited_app(stores, 2, lambda: now[0]).test_client()
    sign_up(viewer, role="client")
    codes = [viewer.get(f"/workers/00000000-0000-4000-8000-0000000000{n:02d}").status_code for n in range(3)]
    assert codes == [404, 404, 429]


def test_signing_in_again_does_not_reset_the_allowance(stores):
    now = [1000.0]
    limited = limited_app(stores, 1, lambda: now[0])
    first = limited.test_client()
    number, _ = sign_up(first, role="client")
    assert first.get("/workers/00000000-0000-4000-8000-000000000001").status_code == 404
    second = limited.test_client()
    assert second.post("/auth/sessions", json={"phone": number, "pin": PIN}).status_code == 200
    assert second.get("/workers/00000000-0000-4000-8000-000000000001").status_code == 429


def test_the_limiter_rejects_a_nonsense_setting():
    with pytest.raises(ValueError):
        SlidingWindowLimiter(0, 60)


def test_the_limiter_forgets_idle_clients():
    from kaziforce_api import ratelimit

    now = [0.0]
    limiter = SlidingWindowLimiter(1, 10, clock=lambda: now[0])
    for i in range(ratelimit.MAX_KEYS + 2):
        limiter.retry_after(f"k{i}")
    now[0] = 100.0
    limiter.retry_after("late")
    assert len(limiter._hits) < 10


# Logs, errors, headers, start-up

def test_nothing_personal_reaches_the_logs(app, stores, caplog):
    with caplog.at_level(logging.DEBUG):
        worker, number, _ = named_worker(app, stores, first="Zuberi", last="Mwangangi")
        worker.put("/workers/me", json={**PROFILE, "contact_consent": False})
        worker.put("/workers/me", json={**PROFILE, "first_name": "1"})  # an error
        viewer, viewer_number = client_account(app)
        trade_sample(viewer)
        viewer.get("/workers/not-an-id")
        app.test_client().post("/auth/sessions", json={"phone": number, "pin": "0000"})
    for secret in (number, viewer_number, number[3:], "Zuberi", "Mwangangi", PIN):
        assert secret not in caplog.text


def test_error_messages_never_echo_what_was_sent(app):
    _, response = sign_up(app.test_client(), first="Bad<name>1")
    assert response.status_code == 400 and "Bad<name>1" not in response.get_data(as_text=True)


def test_every_response_carries_the_security_headers(app):
    response = app.test_client().get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in response.headers  # not in development


def production(monkeypatch, stores, origin="https://app.example.org"):
    service, accounts = stores
    monkeypatch.setenv("KAZIFORCE_ENV", "production")
    if origin:
        monkeypatch.setenv("KAZIFORCE_CORS_ORIGIN", origin)
    else:
        monkeypatch.delenv("KAZIFORCE_CORS_ORIGIN", raising=False)
    return create_app(service, accounts=accounts)


def test_hsts_and_secure_cookies_are_for_production_only(app, stores, monkeypatch):
    live = production(monkeypatch, stores)
    assert "max-age=" in live.test_client().get("/health").headers["Strict-Transport-Security"]
    cookie = sign_up(live.test_client(), role="client")[1].headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    monkeypatch.setenv("KAZIFORCE_ENV", "test")
    assert "Secure" not in sign_up(app.test_client(), role="client")[1].headers["Set-Cookie"]


def test_cors_allows_only_the_configured_origin_in_production(stores, monkeypatch):
    live = production(monkeypatch, stores)
    allowed = live.test_client().get("/health", headers={"Origin": "https://app.example.org"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "https://app.example.org"
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000", "https://evil.example.org"):
        assert "Access-Control-Allow-Origin" not in live.test_client().get("/health", headers={"Origin": origin}).headers


def test_production_refuses_to_start_without_a_cors_origin(stores, monkeypatch):
    with pytest.raises(ConfigError, match="KAZIFORCE_CORS_ORIGIN"):
        production(monkeypatch, stores, origin=None)


def test_a_wildcard_origin_is_refused(stores, monkeypatch):
    with pytest.raises(ConfigError):
        production(monkeypatch, stores, origin="*")


def test_production_refuses_to_build_accounts_without_keys(monkeypatch, pg_connect):
    monkeypatch.setenv("KAZIFORCE_ENV", "production")
    monkeypatch.delenv("KAZIFORCE_FIELD_KEY", raising=False)
    monkeypatch.delenv("KAZIFORCE_PHONE_HMAC_KEY", raising=False)
    with pytest.raises(ConfigError, match="KAZIFORCE_FIELD_KEY"):
        AccountStore(pg_connect)


def test_the_wrong_field_key_signs_no_one_in_and_shows_nothing(app, stores, pg_connect, crypto, caplog):
    import base64

    from kaziforce_api.crypto import FieldCipher, FieldCrypto, generate_key

    worker, number, _ = named_worker(app, stores, first="Zuberi", last="Mwangangi")
    token = worker.get_cookie("kaziforce_session").value
    wrong = AccountStore(pg_connect, FieldCrypto(FieldCipher({"v1": base64.urlsafe_b64decode(generate_key())}),
                                                 crypto.phone_hmac_key))
    with caplog.at_level(logging.DEBUG):
        assert wrong.session_account(token) is None  # the stored number will not decrypt
    assert number not in caplog.text and "Zuberi" not in caplog.text
    assert stores[1].session_account(token).phone == f"254{number}"  # the right key still does


def test_the_demo_workers_are_seeded_once_and_appear_named_in_their_trade(app, stores, pg_connect, crypto):
    from kaziforce_api.data.demo import DEMO_WORKERS, seed_demo_workers
    from kaziforce_api.data.seed import SkillDescriber

    accounts = stores[1]
    store = PostgresProfileStore(pg_connect)
    assert len(seed_demo_workers(accounts, store, SkillDescriber())) == len(DEMO_WORKERS)
    assert seed_demo_workers(accounts, store, SkillDescriber()) == []  # idempotent

    # a worker who withdrew is brought back, so a test that withdrew cannot leave the demo bare
    amina = app.test_client()
    assert amina.post("/auth/sessions", json={"phone": "700000001", "pin": "4821"}).status_code == 200
    own = amina.get("/workers/me").get_json()["worker"]
    own_fields = {k: own[k] for k in ("biography", "skills", "location", "availability", "rate_expectation")}
    withdrawn = amina.put("/workers/me", json={**own_fields, "contact_consent": False})
    assert withdrawn.get_json()["contact"]["consent"] is False
    assert seed_demo_workers(accounts, store, SkillDescriber()) == []
    assert amina.get("/workers/me").get_json()["contact"]["consent"] is True

    viewer, _ = client_account(app)
    plumbing = {**JOB, "title": "Fix bathroom leakage", "description": "Need a fundi bomba. Bathroom leaking.",
                "required_skills": ["replace faucets", "plumbing tools"]}
    posted = viewer.post("/jobs", json=plumbing).get_json()["interpretation"]["worker_pool"][0]
    names = [c["name"] for c in posted["sample"] if "name" in c]
    assert names[:3] == ["Amina Wanjiru", "Joseph Otieno", "Grace Achieng"]
    first = next(c for c in posted["sample"] if c.get("name") == "Amina Wanjiru")
    body = viewer.get(f"/workers/{first['public_id']}").get_json()
    assert body["contact"]["phone_local"] == "700000001" and body["trade"] == "plumber"
