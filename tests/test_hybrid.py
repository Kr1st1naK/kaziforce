"""combine() (Equation 3.1) and HybridScorer."""

import numpy as np
import pytest

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, JobPosting, WorkerProfile
from kaziforce_api.matching.hybrid import HybridScorer, HybridWeights, combine
from kaziforce_api.matching.rule_based import RuleBasedScorer
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_kg.enrichment import NullEnricher


def test_combine_equal_weights():
    weights = HybridWeights(alpha=0.5, beta=0.5)
    assert combine(1.0, 0.0, weights) == 0.5
    assert combine(0.0, 1.0, weights) == 0.5


def test_combine_default_weights_sum_to_one():
    weights = HybridWeights()
    assert weights.alpha + weights.beta == 1.0


# HybridScorer

def _letters(texts):
    return np.array([[t.lower().count(c) for c in "abcdefghijklmnopqrstuvwxyz"] for t in texts], dtype=float) + 1e-3


def _pair():
    e = NullEnricher()
    w = WorkerProfile("w", "pipe fitter in Kisumu", ("fix pipes",), "Kisumu", "Part-time", 1000.0)
    jobs = [JobPosting("a", "Pipes", "fix pipes in Kisumu", ("fix pipes",), "Kisumu", "Part-time", 1500.0),
            JobPosting("b", "Payroll", "monthly payroll", ("payroll",), None, None, None)]
    return (EnrichedWorker(w, e.enrich(w.biography, w.skills)),
            [EnrichedJob(j, e.enrich(j.description, j.required_skills)) for j in jobs])


def test_hybrid_scorer_combines_both_components_and_keeps_the_breakdown():
    worker, jobs = _pair()
    semantic = SemanticScorer(encoder=_letters)
    results = HybridScorer(RuleBasedScorer(), semantic).score_all(worker, jobs)
    expected_sem = semantic.score_many(worker, jobs)
    for m, rule_job, s in zip(results, jobs, expected_sem):
        r = RuleBasedScorer().score(worker, rule_job)
        assert (m.rule, m.semantic) == (r.score, pytest.approx(float(s)))
        assert m.composite == pytest.approx(0.5 * r.score + 0.5 * float(s))
        assert m.components == r.components
    assert results[0].rule == pytest.approx(1.0) and results[1].components["location"] is None


def test_hybrid_weights_override_and_validation():
    worker, jobs = _pair()
    scorer = HybridScorer(RuleBasedScorer(), SemanticScorer(encoder=_letters))
    rule_only = scorer.score_all(worker, jobs, weights=HybridWeights(alpha=1.0, beta=0.0))
    assert [m.composite for m in rule_only] == [m.rule for m in rule_only]
    with pytest.raises(ValueError):
        scorer.score_all(worker, jobs, weights=HybridWeights(alpha=0.0, beta=0.0))
