"""
Rule-based matching component.

Scores a worker-job pair on: skill overlap, location, budget, and
availability, as fixed in docs/scoring-policy.md §1 before any score existed.

The weights are assigned a priori from domain reasoning and are deliberately
NOT tuned against the evaluation labels. The reference relevance labels are
occupational (same area) and ignore location, budget and availability, so
tuning against them would drive those weights to zero as an artefact of the
labelling rather than as a finding.

Missing fields: a criterion is scored only when its field is present on both
sides; absent criteria are dropped and the remaining weights renormalised.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, MatchedSkill

CRITERIA = ("skill_overlap", "location", "budget_fit", "availability")
FULL_TIME = "full-time"


@dataclass(frozen=True)
class RuleBasedWeights:
    skill_overlap: float = 0.4
    location: float = 0.2
    budget: float = 0.2
    availability: float = 0.2

    def by_criterion(self) -> dict[str, float]:
        w = asdict(self)
        return {"skill_overlap": w["skill_overlap"], "location": w["location"], "budget_fit": w["budget"],
                "availability": w["availability"]}


@dataclass(frozen=True)
class RuleResult:
    score: float
    components: dict[str, float | None]   # None = criterion absent (field missing on either side)
    matched_skills: tuple[MatchedSkill, ...]


# Criteria (each returns a score in [0, 1], or None when the criterion is absent)

def skill_overlap(worker_skills: frozenset[str], job_skills: frozenset[str]) -> float | None:
    if not worker_skills or not job_skills:
        return None
    return len(worker_skills & job_skills) / len(job_skills)


def _clean(value: str | None) -> str | None:
    return value.strip().casefold() if value and value.strip() else None


def location_match(worker: str | None, job: str | None) -> float | None:
    a, b = _clean(worker), _clean(job)
    if a is None or b is None:
        return None
    if a == b:
        return 1.0
    return 0.5 if a.split(" - ")[0].strip() == b.split(" - ")[0].strip() else 0.0


def budget_fit(rate: float | None, budget: float | None) -> float | None:
    if rate is None or budget is None or budget <= 0:
        return None
    return 1.0 if rate <= budget else max(0.0, 1.0 - (rate - budget) / budget)


def availability_match(worker: str | None, job: str | None) -> float | None:
    a, b = _clean(worker), _clean(job)
    if a is None or b is None:
        return None
    return 1.0 if a == b or a == FULL_TIME else 0.0


def combine_present(components: dict[str, float | None], weights: dict[str, float]) -> float:
    """Weighted mean over the criteria that are present; 0 if none is."""
    present = {c: s for c, s in components.items() if s is not None}
    total = sum(weights[c] for c in present)
    return sum(weights[c] * s for c, s in present.items()) / total if total else 0.0


class RuleBasedScorer:
    def __init__(self, weights: RuleBasedWeights = RuleBasedWeights()):
        self.weights = self._checked(weights)

    def score(self, worker: EnrichedWorker, job: EnrichedJob, weights: RuleBasedWeights | None = None) -> RuleResult:
        """Rule-based score of one pair. `weights` overrides the scorer's own weights for this call only."""
        w = self._checked(weights) if weights is not None else self.weights
        worker_skills = worker.enrichment.skills
        job_skills = job.enrichment.stated_skills
        components = {
            "skill_overlap": skill_overlap(worker_skills, job_skills),
            "location": location_match(worker.profile.location, job.profile.location),
            "budget_fit": budget_fit(worker.profile.rate_expectation, job.profile.budget),
            "availability": availability_match(worker.profile.availability, job.profile.availability),
        }
        evidence = {e.skill: e for e in worker.enrichment.evidence}
        matched = tuple(MatchedSkill(e.skill, e.skill_label, e.source, e.graph_path)
                        for skill in (j.skill for j in job.enrichment.evidence)
                        if skill in job_skills and skill in evidence for e in [evidence[skill]])
        return RuleResult(combine_present(components, w.by_criterion()), components, matched)

    @staticmethod
    def _checked(weights: RuleBasedWeights) -> RuleBasedWeights:
        values = weights.by_criterion().values()
        if any(v < 0 for v in values) or not any(values):
            raise ValueError(f"rule-based weights must be non-negative and not all zero: {weights}")
        return weights
