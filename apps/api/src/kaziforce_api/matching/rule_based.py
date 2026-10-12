"""
Rule-based matching component.

Scores a worker-job pair on: skill overlap, location, budget, and
availability.

The weights are assigned a priori from domain reasoning and are deliberately
NOT tuned against the evaluation labels. The reference relevance labels are
occupational (same area) and ignore location, budget and availability, so
tuning against them would drive those weights to zero as an artefact of the
labelling rather than as a finding.
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
