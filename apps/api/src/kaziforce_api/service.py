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

A posting stored through create_job() joins the live candidate pool, so the
pool grows during a demo. The evaluation never uses this service: it builds its
own Recommender from the frozen CSV dataset (scripts/evaluate.py), so published
metrics always come from exactly the 280 committed postings.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable, Sequence

from kaziforce_api.data.models import JobPosting, MatchScore, WorkerProfile
from kaziforce_api.data.seed import SkillDescriber
from kaziforce_api.data.store import CsvProfileStore, PostgresProfileStore, ProfileStore
from kaziforce_api.matching.semantic import SemanticScorer, job_text
from kaziforce_api.pipeline import CONFIGURATIONS, Recommender, build_recommender
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.enrichment import STATED_SOURCES, Enrichment
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
        self._semantic: SemanticScorer | None = None
        self._describer: SkillDescriber | None = None
        self._lock = threading.Lock()  # held while the candidate pool is rebuilt

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
            self.kg, self._semantic = KnowledgeGraphBuilder().build(), self._semantic_factory()
            self._describer = SkillDescriber()
            self._rebuild(jobs)
            self.startup_seconds = time.perf_counter() - started
            self._ready.set()
            log.info("recommendation engine ready in %.1f s", self.startup_seconds)
        except BaseException as exc:  # reported through /health and as 500s
            self.startup_error = exc
            log.exception("recommendation engine failed to start")

    def _rebuild(self, jobs: Sequence[JobPosting]) -> None:
        """Build every configuration over this candidate pool. Job texts already embedded stay cached."""
        with self._lock:
            recommenders = {n: build_recommender(n, jobs, kg=self.kg, semantic=self._semantic, k=MAX_K)
                            for n in CONFIGURATIONS}
            self._semantic.embed([job_text(j) for j in recommenders["full"].jobs])
            self.recommenders = recommenders
            self._jobs = {j.posting_id: j for j in jobs}

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    @property
    def candidate_jobs(self) -> int:
        return len(self._jobs)

    def _require_ready(self) -> None:
        if self.startup_error:
            raise RuntimeError("the recommendation engine failed to start") from self.startup_error
        if not self.ready:
            raise NotReady("the recommendation engine is still loading")

    # Queries

    def worker(self, worker_id: str) -> WorkerProfile:
        """A stored worker profile; KeyError if unknown."""
        return self.store.worker(worker_id)

    def job(self, posting_id: str) -> JobPosting:
        """A stored job posting; KeyError if unknown."""
        return self.store.job(posting_id)

    def recommend(self, worker: WorkerProfile, k: int, configuration: str, stored: bool) -> dict:
        self._require_ready()
        recommender = self.recommenders[configuration]
        started = time.perf_counter()
        results = recommender.rank(worker, k=k)
        enrichment = recommender.enrich(worker).enrichment
        elapsed = 1000 * (time.perf_counter() - started)
        return {
            "configuration": configuration, "k": k,
            "worker": self._worker_payload(worker, stored),
            "enrichment": self._enrichment_payload(enrichment),
            "results": [self._result(m) for m in results],
            "timing_ms": round(elapsed, 1),
        }

    # Stored profiles

    def create_worker(self, profile: WorkerProfile) -> dict:
        """Store a new worker profile and return it with its identifier and enrichment."""
        self._require_ready()
        stored = self.store.save_worker(profile, self._describer.describe(profile.skills))
        enrichment = self.recommenders["full"].enrich(stored).enrichment
        return {"worker_id": stored.worker_id, "worker": self._worker_payload(stored, stored=True),
                "enrichment": self._enrichment_payload(enrichment)}

    def create_job(self, posting: JobPosting) -> dict:
        """Store a new posting, add it to the live candidate pool, and return how it was understood."""
        self._require_ready()
        stored = self.store.save_job(posting, self._describer.describe(posting.required_skills))
        self._rebuild([*self._jobs.values(), stored])
        return self.job_interpretation(stored)

    def job_interpretation(self, posting: JobPosting) -> dict:
        """How the engine reads one posting: terms, occupations, its stated skills, and the matching worker pool.

        Only the posting's stated skills are reported. Skills the knowledge graph could infer from
        the occupation are deliberately left out, because matching uses stated requirements only
        (docs/scoring-policy.md §1).
        """
        self._require_ready()
        recommender = self.recommenders["full"]
        enrichment = recommender.enricher.enrich(posting.description, posting.required_skills)
        stated = [e for e in enrichment.evidence if e.source in STATED_SOURCES]
        return {
            "posting_id": posting.posting_id,
            "job": {"posting_id": posting.posting_id, "title": posting.title, "description": posting.description,
                    "required_skills": list(posting.required_skills), "location": posting.location,
                    "availability": posting.availability, "budget": posting.budget},
            "interpretation": {
                **self._enrichment_payload(enrichment),
                "stated_skills": [{"skill": e.skill, "skill_label": e.skill_label, "source": e.source} for e in stated],
                "worker_pool": self._worker_pool(enrichment),
            },
            "candidate_jobs": self.candidate_jobs,
        }

    def _worker_pool(self, enrichment: Enrichment) -> list[dict]:
        """Stored workers whose own enrichment reaches each occupation this posting reaches.

        Counted from the profiles themselves, never from the dataset's occupational area labels.
        """
        if not enrichment.occupations:
            return []
        enricher = self.recommenders["full"].enricher
        reached = [enricher.enrich(w.biography, w.skills).occupations for w in self.store.workers()]
        return [{"occupation": self._node_ref(o), "workers": sum(o in occupations for occupations in reached)}
                for o in enrichment.occupations]

    # Serialisation

    @staticmethod
    def _worker_payload(worker: WorkerProfile, stored: bool) -> dict:
        return {"worker_id": worker.worker_id if stored else None, "biography": worker.biography,
                "skills": list(worker.skills), "location": worker.location,
                "availability": worker.availability, "rate_expectation": worker.rate_expectation}

    def _enrichment_payload(self, enrichment: Enrichment) -> dict:
        return {"terms": [self._node_ref(t) for t in enrichment.terms],
                "occupations": [self._node_ref(o) for o in enrichment.occupations],
                "unmapped": list(enrichment.unmapped)}

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
