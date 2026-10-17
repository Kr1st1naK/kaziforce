"""
The recommendation pipeline: enrich, score, rank (worker -> jobs).

A Recommender is an (enricher, scorer) pair plus the candidate jobs. The
command-line demo, the evaluation runner and (later) the API all rank through
this class, so the chain that is demonstrated is the chain that is evaluated.
Configurations differ only in the objects supplied (CONFIGURATIONS below),
never in conditional logic inside the scorers.

Ranking: descending composite score; ties are broken by one fixed random
order of the postings (seed 42), identical for every configuration
(docs/scoring-policy.md §5).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import replace

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, JobPosting, MatchScore, WorkerProfile
from kaziforce_api.matching.base import Scorer
from kaziforce_api.matching.hybrid import HybridScorer
from kaziforce_api.matching.keyword import KeywordScorer
from kaziforce_api.matching.rule_based import RuleBasedScorer
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_kg.enrichment import Enricher, NullEnricher, ProfileEnricher
from kaziforce_kg.graph import KnowledgeGraph

TIE_BREAK_SEED = 42


class Recommender:
    def __init__(self, enricher: Enricher, scorer: Scorer, jobs: Sequence[JobPosting], k: int = 10,
                 tie_break_seed: int = TIE_BREAK_SEED):
        self.enricher, self.scorer, self.k = enricher, scorer, k
        self.jobs = [EnrichedJob(j, enricher.enrich(j.description, j.required_skills)) for j in jobs]
        order = sorted(j.posting_id for j in jobs)
        random.Random(tie_break_seed).shuffle(order)
        self._tie_order = {pid: i for i, pid in enumerate(order)}

    def enrich(self, worker: WorkerProfile) -> EnrichedWorker:
        return EnrichedWorker(worker, self.enricher.enrich(worker.biography, worker.skills))

    def rank(self, worker: WorkerProfile, k: int | None = None) -> list[MatchScore]:
        """Top-k MatchScores (rank 1 = best). k=None uses the recommender's k; k=0 returns every job."""
        scores = self.scorer.score_all(self.enrich(worker), self.jobs)
        ranked = sorted(scores, key=lambda m: (-m.composite, self._tie_order[m.posting_id]))
        k = self.k if k is None else k
        return [replace(m, rank=i) for i, m in enumerate(ranked[:k] if k else ranked, start=1)]


# Configurations: name -> (needs the KG?, factory building the (enricher, scorer) pair)

Factory = Callable[[KnowledgeGraph | None, SemanticScorer, Sequence[JobPosting]], tuple[Enricher, Scorer]]

CONFIGURATIONS: dict[str, tuple[bool, Factory]] = {
    "keyword": (False, lambda kg, sem, jobs: (NullEnricher(), KeywordScorer(jobs))),
    "rule_only": (False, lambda kg, sem, jobs: (NullEnricher(), RuleBasedScorer())),
    "semantic_only": (False, lambda kg, sem, jobs: (NullEnricher(), sem)),
    "hybrid_no_kg": (False, lambda kg, sem, jobs: (NullEnricher(), HybridScorer(RuleBasedScorer(), sem))),
    "full": (True, lambda kg, sem, jobs: (ProfileEnricher(kg), HybridScorer(RuleBasedScorer(), sem))),
}


def build_recommender(name: str, jobs: Sequence[JobPosting], kg: KnowledgeGraph | None = None,
                      semantic: SemanticScorer | None = None, k: int = 10) -> Recommender:
    """Recommender for a named configuration. Pass one SemanticScorer to share its embedding cache."""
    if name not in CONFIGURATIONS:
        raise ValueError(f"unknown configuration {name!r}; choose from {list(CONFIGURATIONS)}")
    needs_kg, factory = CONFIGURATIONS[name]
    if needs_kg and kg is None:
        raise ValueError(f"configuration {name!r} needs the knowledge graph")
    enricher, scorer = factory(kg, semantic or SemanticScorer(), jobs)
    return Recommender(enricher, scorer, jobs, k=k)
