"""
Hybrid scoring: linear combination of rule-based and semantic scores.

final_score = alpha * rule_based_score + beta * semantic_score

alpha and beta are tuned on the validation subset to maximise MRR
(see proposal Section 3.2.3, Equation 3.1).
"""

from dataclasses import dataclass


@dataclass
class HybridWeights:
    alpha: float = 0.5
    beta: float = 0.5


def combine(rule_based_score: float, semantic_score: float, weights: HybridWeights) -> float:
    return weights.alpha * rule_based_score + weights.beta * semantic_score
