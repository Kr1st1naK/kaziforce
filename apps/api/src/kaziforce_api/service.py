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
from kaziforce_api.data.store import CsvProfileStore, PostgresProfileStore, ProfileStore, ReadOnlyStore
from kaziforce_api.explainability.explain import ExplanationGenerator
from kaziforce_api.matching.bands import DISPLAY_THRESHOLD, band, match_score
from kaziforce_api.matching.semantic import SemanticScorer, job_text
from kaziforce_api.pipeline import CONFIGURATIONS, Recommender, build_recommender
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.enrichment import STATED_SOURCES, Enrichment
from kaziforce_kg.graph import KnowledgeGraph

log = logging.getLogger(__name__)
MAX_K = 50
TRADE_SAMPLE_SIZE = 5  # rows shown under "Workers in this trade"
SAMPLE_LENGTH = 120  # characters of a worker's own words shown in that list


def shorten(text: str, limit: int = SAMPLE_LENGTH) -> str:
    """Trims to a whole word, or a whole skill, so a client never reads half of one."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = head.rsplit(", ", 1)[0] if ", " in head else head.rsplit(" ", 1)[0]
    return f"{cut.rstrip(' ,')}\u2026"
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
        self.explainer: ExplanationGenerator | None = None
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
            self.explainer = ExplanationGenerator(self.kg)
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
        # Timed first, persisted after: recording the ranking is bookkeeping, not part of
        # answering the query, and NFR-01 measures the query.
        if stored:
            self._persist(worker.worker_id, configuration, results)
        return {
            "configuration": configuration, "k": k,
            "worker": self._worker_payload(worker, stored),
            "enrichment": self._enrichment_payload(enrichment),
            "results": [self._result(m, worker) for m in results],
            "display_threshold": DISPLAY_THRESHOLD,
            "timing_ms": round(elapsed, 1),
        }

    def _persist(self, worker_id: str, configuration: str, results: Sequence[MatchScore]) -> None:
        """Record the ranking as match_score rows (FR-11), replacing this worker's previous one.

        Replacing rather than appending keeps one current ranking per (worker, configuration):
        otherwise every refresh of the matches screen would add another ten rows, and the table
        would record how often somebody looked rather than what the engine decided.

        A failure here must not cost the worker their results. The ranking has already been
        computed and is about to be returned; a bookkeeping write that fails is logged and
        swallowed. A read-only store simply cannot do it, which is not an error.
        """
        try:
            self.store.save_match_scores(worker_id, configuration, results, replace=True)
        except ReadOnlyStore:
            pass
        except Exception:
            log.exception("could not record the ranking for worker %s", worker_id)

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

    def worker_profile(self, worker: WorkerProfile) -> dict:
        """One stored worker profile with its enrichment, for the profile screen."""
        self._require_ready()
        enrichment = self.recommenders["full"].enrich(worker).enrichment
        return {"worker_id": worker.worker_id, "worker": self._worker_payload(worker, stored=True),
                "enrichment": self._enrichment_payload(enrichment)}

    def posting_summary(self, posting: JobPosting) -> dict:
        """A posting as a row in the client's list: the facts, and the trade it was matched to."""
        self._require_ready()
        enrichment = self.recommenders["full"].enricher.enrich(posting.description, posting.required_skills)
        return {"posting_id": posting.posting_id, "title": posting.title, "location": posting.location,
                "availability": posting.availability, "budget": posting.budget,
                "trades": [self._node_ref(o) for o in enrichment.occupations]}

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
        Each entry carries a short sample for display: how the worker describes their own work,
        where they are, when they work and their rate. No identifier, no score and no ranking,
        so a client cannot enumerate or rank workers from it.
        """
        if not enrichment.occupations:
            return []
        enricher = self.recommenders["full"].enricher
        reached = [(w, enricher.enrich(w.biography, w.skills).occupations) for w in self.store.workers()]
        pool = []
        for occupation in enrichment.occupations:
            matching = [w for w, occupations in reached if occupation in occupations]
            pool.append({"occupation": self._node_ref(occupation), "workers": len(matching),
                         "sample": [self._worker_sample(w) for w in matching[:TRADE_SAMPLE_SIZE]]})
        return pool

    @staticmethod
    def _worker_sample(worker: WorkerProfile) -> dict:
        """A worker as a client may see them: their own words, and the practical facts. No identifier."""
        describes_as = ", ".join(worker.skills) if worker.skills else worker.biography
        return {"describes_as": shorten(describes_as), "location": worker.location,
                "availability": worker.availability, "rate_expectation": worker.rate_expectation}

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

    def _skill_type(self, skill: str) -> str | None:
        """ESCO's own split: "skill" is something you do, "knowledge" something you know.

        The interface uses it only for grammar ("needs someone to install sockets" against
        "needs electrical wiring plans"). None for wording that is not in the graph.
        """
        node = self.kg.graph.nodes.get(skill)
        return node.get("skill_type") if node else None

    def _node_ref(self, node: str) -> dict:
        return {"id": node, "label": self.kg.label(node)}

    def _node(self, node: str) -> dict:
        return {"id": node, "label": self.kg.label(node), "type": self.kg.type(node)}

    def _result(self, m: MatchScore, worker: WorkerProfile) -> dict:
        job = self._jobs[m.posting_id]
        return {
            "rank": m.rank, "posting_id": m.posting_id, "title": job.title, "description": job.description,
            "location": job.location, "availability": job.availability, "budget": job.budget,
            "scores": {"composite": m.composite, "rule": m.rule, "semantic": m.semantic},
            "match_score": match_score(m.composite),
            "band": band(m.composite),
            "rule_components": dict(m.components) if m.rule is not None else None,
            "matched_skills": [{"skill": s.skill, "skill_label": s.skill_label, "source": s.source,
                                "skill_type": self._skill_type(s.skill),
                                "graph_path": [{"source": self._node(u), "relation": r, "target": self._node(v)}
                                               for u, r, v in s.graph_path]}
                               for s in m.matched_skills],
            "explanation": self.explainer.explain(worker, job, m).to_dict(),
        }
