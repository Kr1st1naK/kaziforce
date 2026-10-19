"""
Flask REST API: JSON between the Next.js web app (apps/web) and the
recommendation engine (IR-02).

    GET  /health          {"status": "ok", "ready": bool, "candidate_jobs": int}
    POST /recommend       ranked jobs for a stored worker (worker_id) or a typed-in profile (worker)
    POST /workers         store a worker profile; returns its id and enrichment
    POST /jobs            store a job posting, add it to the candidate pool, return how it was understood
    GET  /jobs/<id>       how a stored posting was understood

Contract: docs/api.md. Errors are always {"error": {"code", "message", "field"?}}
with status 400 invalid_request, 404 not_found, 405 method_not_allowed,
501 not_supported (the store cannot accept new profiles), 503 not_ready
(engine still loading) or 500 internal_error; no stack trace is ever returned.

Run with: flask --app kaziforce_api.app run   (Flask finds create_app()).
The engine loads in the background at startup (about 20-30 s on CPU).
"""

from __future__ import annotations

import logging
import math
import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from kaziforce_api.data.models import JobPosting, WorkerProfile
from kaziforce_api.data.store import ReadOnlyStore
from kaziforce_api.pipeline import CONFIGURATIONS
from kaziforce_api.service import MAX_K, NotReady, RecommendationService

AVAILABILITY = ("Full-time", "Part-time", "Weekends")
REQUEST_FIELDS = {"worker_id", "worker", "k", "configuration"}
WORKER_FIELDS = {"biography", "skills", "location", "availability", "rate_expectation"}
JOB_FIELDS = {"title", "description", "required_skills", "location", "availability", "budget"}
MAX_TEXT, MAX_SKILLS, MAX_SKILL_TEXT, MAX_TITLE = 4000, 50, 200, 255
DEFAULT_CORS_ORIGIN = "http://localhost:3000"  # Next.js dev server; override with KAZIFORCE_CORS_ORIGIN


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


def create_app(service: RecommendationService | None = None, start: bool = True) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False
    if service is None:
        service = RecommendationService()
        if start:
            service.start(background=True)
    app.extensions["kaziforce"] = service
    cors_origin = os.getenv("KAZIFORCE_CORS_ORIGIN", DEFAULT_CORS_ORIGIN)

    @app.after_request
    def cors(response):
        if request.headers.get("Origin") == cors_origin:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Vary"] = "Origin"
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok", ready=service.ready, candidate_jobs=service.candidate_jobs)

    @app.route("/recommend", methods=["POST", "OPTIONS"])
    def recommend():
        if request.method == "OPTIONS":
            return "", 204
        worker_id, worker, k, configuration = parse_request(request.get_json(silent=True))
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
        return jsonify(service.create_worker(parse_worker(request.get_json(silent=True)))), 201

    @app.route("/jobs", methods=["POST", "OPTIONS"])
    def create_job():
        if request.method == "OPTIONS":
            return "", 204
        return jsonify(service.create_job(parse_job(request.get_json(silent=True)))), 201

    @app.get("/jobs/<posting_id>")
    def job(posting_id: str):
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
