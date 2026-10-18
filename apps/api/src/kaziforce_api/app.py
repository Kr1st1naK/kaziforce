"""
Flask REST API: JSON between the Next.js web app (apps/web) and the
recommendation engine (IR-02).

    GET  /health       {"status": "ok", "ready": bool}
    POST /recommend    ranked jobs for a stored worker (worker_id) or a typed-in profile (worker)

Contract: docs/api.md. Errors are always {"error": {"code", "message", "field"?}}
with status 400 invalid_request, 404 not_found, 405 method_not_allowed,
503 not_ready (engine still loading) or 500 internal_error; no stack trace is
ever returned.

Run with: flask --app kaziforce_api.app run   (Flask finds create_app()).
The engine loads in the background at startup (about 20-30 s on CPU).
"""

from __future__ import annotations

import logging
import math
import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from kaziforce_api.data.models import WorkerProfile
from kaziforce_api.pipeline import CONFIGURATIONS
from kaziforce_api.service import MAX_K, NotReady, RecommendationService

AVAILABILITY = ("Full-time", "Part-time", "Weekends")
REQUEST_FIELDS = {"worker_id", "worker", "k", "configuration"}
WORKER_FIELDS = {"biography", "skills", "location", "availability", "rate_expectation"}
MAX_TEXT, MAX_SKILLS, MAX_SKILL_TEXT = 4000, 50, 200
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


def parse_worker(body: dict) -> WorkerProfile:
    if not isinstance(body, dict):
        raise InvalidRequest("worker must be an object", "worker")
    unknown = set(body) - WORKER_FIELDS
    if unknown:
        raise InvalidRequest(f"unknown field(s) in worker: {', '.join(sorted(unknown))}", "worker")
    biography = _optional_text(body.get("biography"), "worker.biography")
    if not biography:
        raise InvalidRequest("worker.biography is required", "worker.biography")
    skills = body.get("skills", [])
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        raise InvalidRequest("worker.skills must be a list of strings", "worker.skills")
    skills = [s.strip() for s in skills if s.strip()]
    if len(skills) > MAX_SKILLS or any(len(s) > MAX_SKILL_TEXT for s in skills):
        raise InvalidRequest(f"worker.skills allows at most {MAX_SKILLS} entries of {MAX_SKILL_TEXT} characters",
                             "worker.skills")
    availability = body.get("availability")
    if availability is not None and availability not in AVAILABILITY:
        raise InvalidRequest(f"worker.availability must be one of {', '.join(AVAILABILITY)} or null",
                             "worker.availability")
    rate = body.get("rate_expectation")
    if rate is not None and (isinstance(rate, bool) or not isinstance(rate, (int, float))
                             or not math.isfinite(rate) or rate < 0):
        raise InvalidRequest("worker.rate_expectation must be a non-negative number or null", "worker.rate_expectation")
    return WorkerProfile("", biography, tuple(skills), _optional_text(body.get("location"), "worker.location", 200),
                         availability, float(rate) if rate is not None else None)


def parse_request(body) -> tuple[str | None, WorkerProfile | None, int, str]:
    if not isinstance(body, dict):
        raise InvalidRequest("the request body must be a JSON object")
    unknown = set(body) - REQUEST_FIELDS
    if unknown:
        raise InvalidRequest(f"unknown field(s): {', '.join(sorted(unknown))}")
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
        return jsonify(status="ok", ready=service.ready)

    @app.route("/recommend", methods=["POST", "OPTIONS"])
    def recommend():
        if request.method == "OPTIONS":
            return "", 204
        try:
            worker_id, worker, k, configuration = parse_request(request.get_json(silent=True))
        except InvalidRequest as exc:
            return error(400, "invalid_request", str(exc), exc.field)
        if worker_id is not None:
            try:
                worker = service.worker(worker_id)
            except KeyError:
                return error(404, "not_found", f"no stored worker with id {worker_id}", "worker_id")
        try:
            return jsonify(service.recommend(worker, k, configuration, stored=worker_id is not None))
        except NotReady as exc:
            response = error(503, "not_ready", str(exc))
            response[0].headers["Retry-After"] = "5"
            return response

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        codes = {404: "not_found", 405: "method_not_allowed"}
        return error(exc.code or 500, codes.get(exc.code, "invalid_request" if (exc.code or 500) < 500 else "internal_error"),
                     exc.description or exc.name)

    @app.errorhandler(Exception)
    def internal_error(exc: Exception):
        logging.getLogger(__name__).exception("unhandled error")
        return error(500, "internal_error", "internal server error")

    return app


if __name__ == "__main__":
    create_app().run(debug=False)
