"""
RecommendationService: loads the engine once (graph, postings, model, job
embeddings) and serves recommendations as JSON-ready dicts.

Profiles come from a ProfileStore: PostgreSQL by default (the application
store), or the frozen CSVs with KAZIFORCE_PROFILE_SOURCE=csv (e.g. without a
database). Loading runs in a background thread so the API can answer
"not ready" (503) during startup instead of blocking. Every configuration shares one knowledge
graph and one SemanticScorer, so the model and its embedding cache load once.

Absent values are None (JSON null), never 0: a score component a configuration
does not use, a rule criterion whose field is missing on either side, and a
posting field the posting does not have.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable

from kaziforce_api.data.models import JobPosting, MatchScore, WorkerProfile
from kaziforce_api.data.store import CsvProfileStore, PostgresProfileStore, ProfileStore
from kaziforce_api.matching.semantic import SemanticScorer, job_text
from kaziforce_api.pipeline import CONFIGURATIONS, Recommender, build_recommender
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.graph import KnowledgeGraph

log = logging.getLogger(__name__)
MAX_K = 50
PROFILE_SOURCES = ("db", "csv")


def default_store() -> ProfileStore:
    source = os.getenv("KAZIFORCE_PROFILE_SOURCE", "db")
    if source not in PROFILE_SOURCES:
        raise ValueError(f"KAZIFORCE_PROFILE_SOURCE must be one of {PROFILE_SOURCES}, not {source!r}")
    return PostgresProfileStore() if source == "db" else CsvProfileStore()


class NotReady(RuntimeError):
    pass


class RecommendationService:
    def __init__(self, store: ProfileStore | None = None, semantic_factory: Callable[[], SemanticScorer] = SemanticScorer):
        self.store = store or default_store()
        self._semantic_factory = semantic_factory
        self._ready = threading.Event()
        self.startup_error: BaseException | None = None
        self.startup_seconds: float | None = None
        self.kg: KnowledgeGraph | None = None
        self.recommenders: dict[str, Recommender] = {}
        self._jobs: dict[str, JobPosting] = {}

    # Startup

    def start(self, background: bool = True) -> RecommendationService:
        if background:
            threading.Thread(target=self._load, name="kaziforce-startup", daemon=True).start()
        else:
            self._load()
        return self

    def _load(self) -> None:
        started = time.perf_counter()
        try:
            jobs = self.store.jobs()
            if not jobs:
                raise RuntimeError("the profile store has no job postings; run scripts/seed_database.py")
            self.kg, semantic = KnowledgeGraphBuilder().build(), self._semantic_factory()
            self.recommenders = {n: build_recommender(n, jobs, kg=self.kg, semantic=semantic, k=MAX_K)
                                 for n in CONFIGURATIONS}
            semantic.embed([job_text(j) for j in self.recommenders["full"].jobs])
            self._jobs = {j.posting_id: j for j in jobs}
            self.startup_seconds = time.perf_counter() - started
            self._ready.set()
            log.info("recommendation engine ready in %.1f s", self.startup_seconds)
        except BaseException as exc:  # reported through /health and as 500s
            self.startup_error = exc
            log.exception("recommendation engine failed to start")

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    # Queries

    def worker(self, worker_id: str) -> WorkerProfile:
        """A stored worker profile; KeyError if unknown."""
        return self.store.worker(worker_id)

    def recommend(self, worker: WorkerProfile, k: int, configuration: str, stored: bool) -> dict:
        if self.startup_error:
            raise RuntimeError("the recommendation engine failed to start") from self.startup_error
        if not self.ready:
            raise NotReady("the recommendation engine is still loading")
        recommender = self.recommenders[configuration]
        started = time.perf_counter()
        results = recommender.rank(worker, k=k)
        enrichment = recommender.enrich(worker).enrichment
        elapsed = 1000 * (time.perf_counter() - started)
        return {
            "configuration": configuration, "k": k,
            "worker": {"worker_id": worker.worker_id if stored else None, "biography": worker.biography,
                       "skills": list(worker.skills), "location": worker.location,
                       "availability": worker.availability, "rate_expectation": worker.rate_expectation},
            "enrichment": {"terms": [self._node_ref(t) for t in enrichment.terms],
                           "occupations": [self._node_ref(o) for o in enrichment.occupations],
                           "unmapped": list(enrichment.unmapped)},
            "results": [self._result(m) for m in results],
            "timing_ms": round(elapsed, 1),
        }

    # Serialisation

    def _node_ref(self, node: str) -> dict:
        return {"id": node, "label": self.kg.label(node)}

    def _node(self, node: str) -> dict:
        return {"id": node, "label": self.kg.label(node), "type": self.kg.type(node)}

    def _result(self, m: MatchScore) -> dict:
        job = self._jobs[m.posting_id]
        return {
            "rank": m.rank, "posting_id": m.posting_id, "title": job.title, "description": job.description,
            "location": job.location, "availability": job.availability, "budget": job.budget,
            "scores": {"composite": m.composite, "rule": m.rule, "semantic": m.semantic},
            "rule_components": dict(m.components) if m.rule is not None else None,
            "matched_skills": [{"skill": s.skill, "skill_label": s.skill_label, "source": s.source,
                                "graph_path": [{"source": self._node(u), "relation": r, "target": self._node(v)}
                                               for u, r, v in s.graph_path]}
                               for s in m.matched_skills],
        }
