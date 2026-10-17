"""
Hybrid scoring: linear combination of rule-based and semantic scores.

final_score = alpha * rule_based_score + beta * semantic_score

(proposal Section 3.2.3, Equation 3.1). alpha and beta are assigned a priori
from domain reasoning and are deliberately NOT tuned against the evaluation
labels. The reference relevance labels are occupational (same area) and ignore
location, budget and availability, so tuning against them would favour
whichever component tracks occupation, as an artefact of the labelling rather
than as a finding.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, MatchScore
from kaziforce_api.matching.base import Scorer
from kaziforce_api.matching.rule_based import RuleBasedScorer
from kaziforce_api.matching.semantic import SemanticScorer


@dataclass
class HybridWeights:
    alpha: float = 0.5
    beta: float = 0.5


def combine(rule_based_score: float, semantic_score: float, weights: HybridWeights) -> float:
    return weights.alpha * rule_based_score + weights.beta * semantic_score


class HybridScorer(Scorer):
    """Combines a RuleBasedScorer and a SemanticScorer with combine(); keeps both components and the rule breakdown."""

    def __init__(self, rule: RuleBasedScorer, semantic: SemanticScorer, weights: HybridWeights = HybridWeights()):
        self.rule, self.semantic, self.weights = rule, semantic, weights

    def score_all(self, worker: EnrichedWorker, jobs: Sequence[EnrichedJob],
                  weights: HybridWeights | None = None) -> list[MatchScore]:
        w = weights or self.weights
        if w.alpha < 0 or w.beta < 0 or not (w.alpha or w.beta):
            raise ValueError(f"hybrid weights must be non-negative and not both zero: {w}")
        semantic = self.semantic.score_many(worker, jobs)
        results = []
        for job, s in zip(jobs, semantic):
            r = self.rule.score(worker, job)
            results.append(MatchScore(worker.profile.worker_id, job.profile.posting_id,
                                      composite=combine(r.score, float(s), w), rule=r.score, semantic=float(s),
                                      components=r.components, matched_skills=list(r.matched_skills)))
        return results
