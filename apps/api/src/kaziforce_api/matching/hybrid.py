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

from dataclasses import dataclass


@dataclass
class HybridWeights:
    alpha: float = 0.5
    beta: float = 0.5


def combine(rule_based_score: float, semantic_score: float, weights: HybridWeights) -> float:
    return weights.alpha * rule_based_score + weights.beta * semantic_score
