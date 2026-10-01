"""
Sprint 1: smoke test to confirm the test suite and CI pipeline actually run.
Replace/extend once real scoring logic exists (Sprint 3-4).
"""

from kaziforce_api.matching.hybrid import HybridWeights, combine


def test_combine_equal_weights():
    weights = HybridWeights(alpha=0.5, beta=0.5)
    assert combine(1.0, 0.0, weights) == 0.5
    assert combine(0.0, 1.0, weights) == 0.5


def test_combine_default_weights_sum_to_one():
    weights = HybridWeights()
    assert weights.alpha + weights.beta == 1.0
