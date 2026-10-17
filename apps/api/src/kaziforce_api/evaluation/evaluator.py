"""
Evaluator: ranks every candidate job for each worker of one split, under each
configuration, and computes P@k and reciprocal rank per query.

Only EVALUATION_SPLITS may be evaluated. The test split is reserved for the
final evaluation; allowing it is a deliberate, recorded code change, not a
flag. Relevance labels and variants are read here, on the evaluation side, and
never passed to a recommender.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.evaluation.metrics import first_relevant_rank, precision_at_k
from kaziforce_api.pipeline import Recommender

EVALUATION_SPLITS = ("development",)
VARIANTS = ("formal", "known_alias", "held_out", "minimal")
ALL = "all"


@dataclass(frozen=True)
class QueryResult:
    configuration: str
    worker_id: str
    variant: str
    first_relevant_rank: int | None
    precision: dict[int, float]
    query_ms: float

    @property
    def reciprocal_rank(self) -> float:
        return 1.0 / self.first_relevant_rank if self.first_relevant_rank else 0.0


@dataclass
class RunResult:
    split: str
    ks: tuple[int, ...]
    configurations: list[str]
    queries: list[QueryResult] = field(default_factory=list)

    def summary(self) -> list[dict]:
        """Macro means per configuration x variant (and over all variants), with query-time statistics."""
        groups: dict[tuple[str, str], list[QueryResult]] = defaultdict(list)
        for q in self.queries:
            groups[(q.configuration, q.variant)].append(q)
            groups[(q.configuration, ALL)].append(q)
        rows = []
        for config in self.configurations:
            for variant in (*VARIANTS, ALL):
                qs = groups.get((config, variant))
                if not qs:
                    continue
                times = sorted(q.query_ms for q in qs)
                rows.append({"configuration": config, "variant": variant, "queries": len(qs),
                             **{f"P@{k}": statistics.fmean(q.precision[k] for q in qs) for k in self.ks},
                             "MRR": statistics.fmean(q.reciprocal_rank for q in qs),
                             "median_ms": statistics.median(times), "p95_ms": times[min(len(times) - 1, int(0.95 * len(times)))],
                             "max_ms": times[-1]})
        return rows


class Evaluator:
    def __init__(self, loader: DataLoader, recommenders: dict[str, Recommender], ks: tuple[int, ...] = (3, 5, 10),
                 split: str = "development", max_queries: int | None = None):
        if split not in EVALUATION_SPLITS:
            raise ValueError(f"split {split!r} may not be evaluated; allowed: {EVALUATION_SPLITS} "
                             "(the test split is reserved for the final evaluation)")
        self.loader, self.recommenders, self.ks, self.split, self.max_queries = loader, recommenders, ks, split, max_queries

    def run(self) -> RunResult:
        workers = self.loader.workers(self.split)[: self.max_queries]
        split_of, variants = self.loader.split_of(), self.loader.variants()
        outside = [w.worker_id for w in workers if split_of[w.worker_id] != self.split]
        if outside:
            raise RuntimeError(f"{len(outside)} queries are not in the {self.split} split")
        relevant: dict[str, set[str]] = defaultdict(set)
        for worker_id, posting_id in self.loader.relevance():
            relevant[worker_id].add(posting_id)

        result = RunResult(self.split, self.ks, list(self.recommenders))
        for name, recommender in self.recommenders.items():
            for w in workers:
                start = time.perf_counter()
                ranking = [m.posting_id for m in recommender.rank(w, k=0)]
                elapsed = 1000 * (time.perf_counter() - start)
                rel = relevant[w.worker_id]
                result.queries.append(QueryResult(name, w.worker_id, variants[w.worker_id], first_relevant_rank(ranking, rel),
                                                  {k: precision_at_k(ranking, rel, k) for k in self.ks}, elapsed))
        return result
