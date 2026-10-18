"""Ranking metrics, checked against hand computations."""

import random

import pytest

from kaziforce_api.evaluation.metrics import (
    chance_precision_at_k, chance_reciprocal_rank, first_relevant_rank, precision_at_k, reciprocal_rank,
)

RANKED = ["a", "b", "c", "d", "e", "f"]


@pytest.mark.parametrize("relevant, k, expected", [
    ({"a", "c"}, 3, 2 / 3), ({"a", "c"}, 1, 1.0), ({"f"}, 5, 0.0), ({"f"}, 6, 1 / 6), (set(), 3, 0.0),
    ({"a", "b"}, 10, 0.2),  # k beyond the ranking still divides by k
])
def test_precision_at_k(relevant, k, expected):
    assert precision_at_k(RANKED, relevant, k) == pytest.approx(expected)


def test_precision_at_k_rejects_non_positive_k():
    with pytest.raises(ValueError):
        precision_at_k(RANKED, {"a"}, 0)


@pytest.mark.parametrize("relevant, rank, rr", [({"a"}, 1, 1.0), ({"c", "e"}, 3, 1 / 3), ({"f"}, 6, 1 / 6),
                                                ({"z"}, None, 0.0)])
def test_reciprocal_rank_uses_the_first_relevant_item(relevant, rank, rr):
    assert first_relevant_rank(RANKED, relevant) == rank
    assert reciprocal_rank(RANKED, relevant) == pytest.approx(rr)


def test_p_at_10_ceiling_with_eight_relevant():
    ranked = [f"r{i}" for i in range(8)] + [f"n{i}" for i in range(272)]
    assert precision_at_k(ranked, {f"r{i}" for i in range(8)}, 10) == pytest.approx(0.8)


def test_chance_levels():
    assert chance_precision_at_k(8, 280) == pytest.approx(8 / 280)
    assert chance_reciprocal_rank(1, 4) == pytest.approx((1 + 1 / 2 + 1 / 3 + 1 / 4) / 4)
    assert chance_reciprocal_rank(4, 4) == pytest.approx(1.0)
    rng, n, total = random.Random(0), 20000, 0.0
    for _ in range(n):
        total += 1 / min(rng.sample(range(1, 21), 3))
    assert chance_reciprocal_rank(3, 20) == pytest.approx(total / n, abs=0.01)
