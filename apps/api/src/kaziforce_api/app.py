"""
Flask REST API: JSON between the Next.js web app (apps/web) and the
recommendation engine (IR-02).

    GET    /health            {"status", "ready", "candidate_jobs"}
    POST   /auth/accounts     create an account (phone, PIN, role) and sign in
    POST   /auth/sessions     sign in
    DELETE /auth/sessions     sign out
    GET    /auth/session      who is signed in, and what they own
    POST   /recommend         ranked jobs for the signed-in worker, a worker_id, or a typed-in profile
    GET    /workers/me        the signed-in worker's profile, with their own name and consent
    PUT    /workers/me        replace the signed-in worker's profile (and, if sent, name and consent)
    GET    /workers/<public_id>  a consenting worker's profile and phone number, for a signed-in client
    POST   /workers           store a worker profile; a signed-in worker account claims it
    POST   /jobs              store a posting, add it to the candidate pool, return how it was understood
    GET    /jobs              the signed-in client's postings
    GET    /jobs/<id>         how a stored posting was understood

Contract: docs/api.md. Errors are always {"error": {"code", "message", "field"?}}
with status 400 invalid_request, 401 unauthenticated, 403 forbidden,
404 not_found, 405 method_not_allowed, 409 already_exists, 423 locked, 429 rate_limited,
501 not_supported (the store cannot accept new profiles), 503 not_ready
(engine still loading) or 500 internal_error; no stack trace is ever returned.

Authentication is a proof of concept: see kaziforce_api/auth.py and
docs/limitations.md §7 for what it does and does not protect against.

Run with: flask --app kaziforce_api.app run   (Flask finds create_app()).
The engine loads in the background at startup (about 20-30 s on CPU).
"""

from __future__ import annotations

import logging
import math
import os
import re

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from kaziforce_api.auth import AuthError, check_pin, check_role, local_phone, normalise_phone
from kaziforce_api.crypto import ConfigError, is_production
from kaziforce_api.data.accounts import AccountStore, Contact
from kaziforce_api.data.models import JobPosting, WorkerProfile
from kaziforce_api.data.store import ReadOnlyStore
from kaziforce_api.pipeline import CONFIGURATIONS
from kaziforce_api.ratelimit import SlidingWindowLimiter
from kaziforce_api.service import MAX_K, NotReady, RecommendationService

AVAILABILITY = ("Full-time", "Part-time", "Weekends")
REQUEST_FIELDS = {"worker_id", "worker", "k", "configuration"}
WORKER_FIELDS = {"biography", "skills", "location", "availability", "rate_expectation"}
JOB_FIELDS = {"title", "description", "required_skills", "location", "availability", "budget"}
MAX_TEXT, MAX_SKILLS, MAX_SKILL_TEXT, MAX_TITLE = 4000, 50, 200, 255
# Next.js dev server, both spellings of the loopback address. Override with
# KAZIFORCE_CORS_ORIGIN, which takes a comma-separated list.
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
SESSION_COOKIE = "kaziforce_session"
CREDENTIAL_FIELDS = {"phone", "pin", "role"}
# A worker gives these at sign-up; a client gives none of them.
CONTACT_FIELDS = {"first_name", "last_name", "contact_consent"}
MAX_NAME = 60
# Letters (any script), then single spaces, hyphens, apostrophes or full stops between parts.
NAME_PATTERN = re.compile(r"^[^\W\d_]+(?:[ '’.\-][^\W\d_]+)*\.?$")
# Contact details are released slowly: this many profile views per account per window.
CONTACT_VIEWS_PER_WINDOW, CONTACT_WINDOW_SECONDS = 30, 60
UNAVAILABLE = "This worker's profile is not available."


class Unauthenticated(Exception):
    pass


class Forbidden(Exception):
    def __init__(self, message: str = "This account cannot do that."):
        super().__init__(message)


class InvalidRequest(ValueError):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


def error(status: int, code: str, message: str, field: str | None = None):
    body = {"code": code, "message": message}
    if field:
        body["field"] = field
    return jsonify(error=body), status


def _optional_text(value, field: str, limit: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidRequest(f"{field} must be a string or null", field)
    value = value.strip()
    if len(value) > limit:
        raise InvalidRequest(f"{field} is longer than {limit} characters", field)
    return value or None


def _required_text(value, field: str, limit: int = MAX_TEXT) -> str:
    text = _optional_text(value, field, limit)
    if not text:
        raise InvalidRequest(f"{field} is required", field)
    return text


def _skill_list(value, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(s, str) for s in value):
        raise InvalidRequest(f"{field} must be a list of strings", field)
    skills = [s.strip() for s in value if s.strip()]
    if len(skills) > MAX_SKILLS or any(len(s) > MAX_SKILL_TEXT for s in skills):
        raise InvalidRequest(f"{field} allows at most {MAX_SKILLS} entries of {MAX_SKILL_TEXT} characters", field)
    return tuple(dict.fromkeys(skills))


def _availability(value, field: str) -> str | None:
    if value is not None and value not in AVAILABILITY:
        raise InvalidRequest(f"{field} must be one of {', '.join(AVAILABILITY)} or null", field)
    return value


def _amount(value, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise InvalidRequest(f"{field} must be a non-negative number or null", field)
    return float(value)


def _object(body, name: str) -> dict:
    if not isinstance(body, dict):
        raise InvalidRequest(f"{name} must be an object", name)
    return body


def _no_unknown_fields(body: dict, allowed: set[str], name: str | None = None) -> None:
    unknown = set(body) - allowed
    if unknown:
        where = f" in {name}" if name else ""
        raise InvalidRequest(f"unknown field(s){where}: {', '.join(sorted(unknown))}", name)


def parse_worker(body: dict) -> WorkerProfile:
    body = _object(body, "worker")
    _no_unknown_fields(body, WORKER_FIELDS, "worker")
    return WorkerProfile("", _required_text(body.get("biography"), "worker.biography"),
                         _skill_list(body.get("skills"), "worker.skills"),
                         _optional_text(body.get("location"), "worker.location", 200),
                         _availability(body.get("availability"), "worker.availability"),
                         _amount(body.get("rate_expectation"), "worker.rate_expectation"))


def _person_name(value, field: str) -> str:
    """A first or last name: trimmed, single-spaced, letters with the usual joiners, at most MAX_NAME long."""
    text = " ".join(_required_text(value, field, MAX_NAME).split())
    if not NAME_PATTERN.match(text):
        raise InvalidRequest(f"{field} may contain only letters, spaces, hyphens and apostrophes", field)
    return text


def _consent(value, field: str = "contact_consent") -> bool:
    if not isinstance(value, bool):
        raise InvalidRequest(f"{field} must be true or false", field)
    return value


def parse_signup_contact(body: dict, role: str) -> Contact | None:
    """A new worker's name and consent. A worker must give both and agree; a client gives none."""
    if role != "worker":
        for field in sorted(CONTACT_FIELDS):
            if body.get(field) is not None:
                raise InvalidRequest(f"{field} is only for worker accounts", field)
        return None
    first, last = _person_name(body.get("first_name"), "first_name"), _person_name(body.get("last_name"), "last_name")
    if body.get("contact_consent") is not True:
        raise InvalidRequest("contact_consent: you need to agree that clients can see your name and phone number",
                             "contact_consent")
    return Contact(first, last, True)


def parse_credentials(body, require_role: bool) -> tuple[str, str, str | None]:
    """(phone, PIN, role) from a sign-in or create-account body. The PIN is never logged."""
    body = _object(body, "body")
    _no_unknown_fields(body, CREDENTIAL_FIELDS | (CONTACT_FIELDS if require_role else set()))
    phone = normalise_phone(_required_text(body.get("phone"), "phone", 20))
    pin = check_pin(body.get("pin"))
    role = check_role(body.get("role")) if require_role else None
    return phone, pin, role


def parse_job(body) -> JobPosting:
    """A job posting as submitted. Category is not accepted: the engine never uses it."""
    body = _object(body, "job")
    _no_unknown_fields(body, JOB_FIELDS)
    return JobPosting("", _required_text(body.get("title"), "title", MAX_TITLE),
                      _required_text(body.get("description"), "description"),
                      _skill_list(body.get("required_skills"), "required_skills"),
                      _optional_text(body.get("location"), "location", 200),
                      _availability(body.get("availability"), "availability"),
                      _amount(body.get("budget"), "budget"))


def parse_request(body) -> tuple[str | None, WorkerProfile | None, int, str]:
    if not isinstance(body, dict):
        raise InvalidRequest("the request body must be a JSON object")
    _no_unknown_fields(body, REQUEST_FIELDS)
    has_id, has_worker = body.get("worker_id") is not None, body.get("worker") is not None
    if has_id == has_worker:
        raise InvalidRequest("send exactly one of worker_id and worker")
    worker_id = body.get("worker_id")
    if has_id and (not isinstance(worker_id, str) or not worker_id.strip()):
        raise InvalidRequest("worker_id must be a non-empty string", "worker_id")
    k = body.get("k", 10)
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= MAX_K:
        raise InvalidRequest(f"k must be an integer from 1 to {MAX_K}", "k")
    configuration = body.get("configuration", "full")
    if configuration not in CONFIGURATIONS:
        raise InvalidRequest(f"configuration must be one of {', '.join(CONFIGURATIONS)}", "configuration")
    worker = parse_worker(body["worker"]) if has_worker else None
    return (worker_id.strip() if has_id else None), worker, k, configuration


def split_contact(body):
    """A PUT /workers/me body as (profile fields, name-and-consent fields)."""
    if not isinstance(body, dict):
        return body, {}
    return ({k: v for k, v in body.items() if k not in CONTACT_FIELDS},
            {k: v for k, v in body.items() if k in CONTACT_FIELDS})


def parse_contact_update(sent: dict, current: dict) -> Contact:
    """The name and consent after an edit: what was sent, over what was there.

    Consent can only be on while there is a first and last name to show, and a name is
    stored whole, so one half cannot be set without the other.
    """
    first = _person_name(sent["first_name"], "first_name") if "first_name" in sent else current["first_name"]
    last = _person_name(sent["last_name"], "last_name") if "last_name" in sent else current["last_name"]
    consent = _consent(sent["contact_consent"]) if "contact_consent" in sent else current["consent"]
    if bool(first) != bool(last):
        missing = "last_name" if first else "first_name"
        raise InvalidRequest(f"{missing} is required", missing)
    if consent and not first:
        raise InvalidRequest("contact_consent: add your first and last name before sharing them", "contact_consent")
    return Contact(first, last, consent)


def create_app(service: RecommendationService | None = None, start: bool = True,
               accounts: AccountStore | None = None, contact_limiter: SlidingWindowLimiter | None = None) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False
    if service is None:
        service = RecommendationService()
        if start:
            service.start(background=True)
    accounts = accounts if accounts is not None else AccountStore()
    service.contact_lookup = accounts.consented_cards
    contact_limiter = contact_limiter or SlidingWindowLimiter(CONTACT_VIEWS_PER_WINDOW, CONTACT_WINDOW_SECONDS)
    app.extensions["kaziforce"] = service
    app.extensions["kaziforce_accounts"] = accounts

    production = is_production()
    configured_origins = os.getenv("KAZIFORCE_CORS_ORIGIN", "").strip()
    if production and not configured_origins:
        raise ConfigError("KAZIFORCE_CORS_ORIGIN must be set outside development, to the web app's origin "
                          "(for example https://app.example.org)")
    cors_origins = {origin.strip() for origin in (configured_origins or DEFAULT_CORS_ORIGINS).split(",") if origin.strip()}
    if "*" in cors_origins:
        raise ConfigError("KAZIFORCE_CORS_ORIGIN cannot be *: the API sends cookies, so it names its origins")

    @app.after_request
    def cors(response):
        origin = request.headers.get("Origin")
        if origin in cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
        return response

    @app.after_request
    def security_headers(response):
        # This is a JSON API, so it needs no content of its own to be framed, sniffed or cached.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers.setdefault("Cache-Control", "no-store")  # nothing here should sit in a shared cache
        if production:
            # Only over HTTPS, and only when told this is production: on plain HTTP it does nothing,
            # and set on a development host it would pin a browser to HTTPS for localhost.
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def current_account():
        return accounts.session_account(request.cookies.get(SESSION_COOKIE))

    def require(role: str | None = None):
        account = current_account()
        if account is None:
            raise Unauthenticated
        if role is not None and account.role != role:
            raise Forbidden(f"This is a {account.role} account; that page is for {role}s.")
        return account

    def with_contact(profile: dict, account) -> dict:
        """A worker's own profile with their own name, consent and number: decrypted for them alone."""
        own = accounts.own_contact(account.account_id)
        return {**profile, "contact": {**own, "phone": local_phone(account.phone)}}

    def session_payload(account) -> dict:
        """Who is signed in, and what they own, so the interface can route and draw its nav."""
        payload = {"account": {"account_id": account.account_id, "phone": local_phone(account.phone),
                               "role": account.role},
                   "worker_profile_id": None, "postings": 0}
        if account.role == "worker":
            payload["worker_profile_id"] = accounts.worker_profile_id(account.account_id)
        else:
            payload["postings"] = len(accounts.posting_ids(account.account_id))
        return payload

    def signed_in(account, status: int = 200):
        response = jsonify(session_payload(account))
        token = accounts.start_session(account.account_id)
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="Lax",
                            secure=production or request.is_secure, max_age=7 * 24 * 3600, path="/")
        return response, status

    @app.route("/auth/accounts", methods=["POST", "OPTIONS"])
    def create_account_route():
        if request.method == "OPTIONS":
            return "", 204
        body = request.get_json(silent=True)
        phone, pin, role = parse_credentials(body, require_role=True)
        return signed_in(accounts.create(phone, pin, role, parse_signup_contact(body, role)), 201)

    @app.route("/auth/sessions", methods=["POST", "DELETE", "OPTIONS"])
    def sessions_route():
        if request.method == "OPTIONS":
            return "", 204
        if request.method == "DELETE":
            accounts.end_session(request.cookies.get(SESSION_COOKIE))
            response = jsonify(signed_out=True)
            response.delete_cookie(SESSION_COOKIE, path="/")
            return response
        phone, pin, _ = parse_credentials(request.get_json(silent=True), require_role=False)
        return signed_in(accounts.authenticate(phone, pin))

    @app.get("/auth/session")
    def session_route():
        return jsonify(session_payload(require()))

    @app.get("/health")
    def health():
        return jsonify(status="ok", ready=service.ready, candidate_jobs=service.candidate_jobs)

    @app.route("/recommend", methods=["POST", "OPTIONS"])
    def recommend():
        if request.method == "OPTIONS":
            return "", 204
        body = request.get_json(silent=True)
        account = current_account()
        if isinstance(body, dict) and body.get("worker_id") is None and body.get("worker") is None:
            # A signed-in worker asking for their own matches.
            if account is None or account.role != "worker":
                raise InvalidRequest("send exactly one of worker_id and worker")
            own = accounts.worker_profile_id(account.account_id)
            if own is None:
                raise Forbidden("Create your profile before asking for matches.")
            body = {**body, "worker_id": own}
        worker_id, worker, k, configuration = parse_request(body)
        if worker_id is not None:
            try:
                worker = service.worker(worker_id)
            except KeyError:
                return error(404, "not_found", f"no stored worker with id {worker_id}", "worker_id")
        return jsonify(service.recommend(worker, k, configuration, stored=worker_id is not None))

    @app.route("/workers", methods=["POST", "OPTIONS"])
    def create_worker():
        if request.method == "OPTIONS":
            return "", 204
        account = current_account()
        if account is not None and account.role != "worker":
            raise Forbidden("This is a client account; only workers have a profile.")
        if account is not None and accounts.worker_profile_id(account.account_id):
            raise AuthError("This account already has a profile.", "already_exists")
        created = service.create_worker(parse_worker(request.get_json(silent=True)))
        if account is not None:
            accounts.claim_worker_profile(account.account_id, created["worker_id"])
        return jsonify(created), 201

    @app.route("/workers/me", methods=["GET", "PUT", "OPTIONS"])
    def my_worker_profile():
        if request.method == "OPTIONS":
            return "", 204
        account = require("worker")
        worker_id = accounts.worker_profile_id(account.account_id)
        if worker_id is None:
            return error(404, "not_found", "This account has no profile yet.")
        if request.method == "GET":
            return jsonify(with_contact(service.worker_profile(service.worker(worker_id)), account))
        # An edit replaces the profile whole: the form always submits every field, so a
        # partial body would silently clear whatever it left out. The name and consent are the
        # exception: left out, they stay as they are, because they belong to the account.
        profile_body, contact_body = split_contact(request.get_json(silent=True))
        profile = parse_worker(profile_body)
        contact = parse_contact_update(contact_body, accounts.own_contact(account.account_id)) if contact_body else None
        updated = service.update_worker(worker_id, profile)
        if contact is not None:
            accounts.update_contact(account.account_id, contact)
        return jsonify(with_contact(updated, account))

    @app.route("/workers/<public_id>", methods=["GET", "OPTIONS"])
    def worker_for_client(public_id: str):
        if request.method == "OPTIONS":
            return "", 204
        account = require("client")
        # Counted before the lookup, and for misses as much as hits, so guessing is as slow as browsing.
        wait = contact_limiter.retry_after(account.account_id)
        if wait is not None:
            response = error(429, "rate_limited", "You are viewing profiles too quickly. Wait a minute and try again.")
            response[0].headers["Retry-After"] = str(wait)
            return response
        contact = accounts.consented_contact(public_id)
        if contact is None:
            return error(404, "not_found", UNAVAILABLE)
        try:
            worker = service.worker(contact["worker_id"])
        except KeyError:
            return error(404, "not_found", UNAVAILABLE)
        return jsonify(service.client_view_of_worker(worker, public_id, contact))

    @app.route("/jobs", methods=["GET", "POST", "OPTIONS"])
    def jobs_route():
        if request.method == "OPTIONS":
            return "", 204
        if request.method == "GET":
            account = require("client")
            return jsonify(postings=[service.posting_summary(service.job(pid))
                                     for pid in accounts.posting_ids(account.account_id)])
        account = current_account()
        if account is not None and account.role != "client":
            raise Forbidden("This is a worker account; only clients post jobs.")
        created = service.create_job(parse_job(request.get_json(silent=True)))
        if account is not None:
            accounts.claim_job_posting(account.account_id, created["posting_id"])
        return jsonify(created), 201

    @app.get("/jobs/<posting_id>")
    def job(posting_id: str):
        account = current_account()
        if account is not None and account.role == "client" and not accounts.owns_posting(account.account_id, posting_id):
            return error(404, "not_found", f"no stored posting with id {posting_id}", "posting_id")
        try:
            posting = service.job(posting_id)
        except KeyError:
            return error(404, "not_found", f"no stored posting with id {posting_id}", "posting_id")
        return jsonify(service.job_interpretation(posting))

    @app.errorhandler(InvalidRequest)
    def invalid_request(exc: InvalidRequest):
        return error(400, "invalid_request", str(exc), exc.field)

    @app.errorhandler(NotReady)
    def not_ready(exc: NotReady):
        response = error(503, "not_ready", str(exc))
        response[0].headers["Retry-After"] = "5"
        return response

    @app.errorhandler(ReadOnlyStore)
    def read_only(exc: ReadOnlyStore):
        return error(501, "not_supported", "this server cannot store new profiles "
                                           "(it is reading the frozen dataset, not a database)")

    @app.errorhandler(Unauthenticated)
    def unauthenticated(exc: Unauthenticated):
        return error(401, "unauthenticated", "Sign in to continue.")

    @app.errorhandler(Forbidden)
    def forbidden(exc: Forbidden):
        return error(403, "forbidden", str(exc))

    @app.errorhandler(AuthError)
    def auth_error(exc: AuthError):
        status = {"invalid_request": 400, "already_exists": 409, "locked": 423}.get(exc.code, 401)
        return error(status, exc.code, str(exc), exc.field)

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        codes = {404: "not_found", 405: "method_not_allowed", 501: "not_supported"}
        return error(exc.code or 500, codes.get(exc.code, "invalid_request" if (exc.code or 500) < 500 else "internal_error"),
                     exc.description or exc.name)

    @app.errorhandler(Exception)
    def internal_error(exc: Exception):
        logging.getLogger(__name__).exception("unhandled error")
        return error(500, "internal_error", "internal server error")

    return app


if __name__ == "__main__":
    create_app().run(debug=False)
