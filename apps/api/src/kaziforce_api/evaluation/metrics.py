"""
Ranking metrics for one query (a worker ranking all candidate jobs).

precision_at_k   share of the top k that are relevant: |relevant ∩ top k| / k
reciprocal_rank  1 / rank of the first relevant job (0 if none is ranked)

Both are averaged over queries (macro mean) by the evaluator; MRR is the mean
reciprocal rank. chance_* give the expected values under a uniformly random
ranking, as a reference level.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb


def precision_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    return sum(1 for pid in ranked[:k] if pid in relevant) / k


def first_relevant_rank(ranked: Sequence[str], relevant: set[str]) -> int | None:
    return next((i for i, pid in enumerate(ranked, start=1) if pid in relevant), None)


def reciprocal_rank(ranked: Sequence[str], relevant: set[str]) -> float:
    rank = first_relevant_rank(ranked, relevant)
    return 1.0 / rank if rank else 0.0


def chance_precision_at_k(n_relevant: int, n_candidates: int) -> float:
    """Expected P@k of a random ranking; it does not depend on k."""
    return n_relevant / n_candidates


def chance_reciprocal_rank(n_relevant: int, n_candidates: int) -> float:
    """Expected 1/R for R the first relevant rank of a random ranking: P(R = r) = C(N-r, m-1) / C(N, m)."""
    total = comb(n_candidates, n_relevant)
    return sum(comb(n_candidates - r, n_relevant - 1) / total / r for r in range(1, n_candidates - n_relevant + 2))
