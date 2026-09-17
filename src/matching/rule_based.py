"""
Rule-based matching component.

Scores a worker-job pair on: skill overlap, location, budget, and
availability, using weights tuned via sensitivity analysis on the
validation subset (see proposal Section 3.2.3, Equation 3.1).
"""

from dataclasses import dataclass


@dataclass
class RuleBasedWeights:
    skill_overlap: float = 0.4
    location: float = 0.2
    budget: float = 0.2
    availability: float = 0.2


def score(worker_profile: dict, job_posting: dict, weights: RuleBasedWeights) -> float:
    """Compute the weighted rule-based match score for one worker-job pair.

    TODO(Sprint 3): implement scoring against enriched (graph-linked) profiles
    """
    raise NotImplementedError
