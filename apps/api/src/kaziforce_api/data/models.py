"""
Domain objects passed through the recommendation engine (proposal Figure 4.6
entities WorkerProfile, JobPosting and MatchScore).

Profiles carry only what a real user would submit. Dataset bookkeeping
(group_id, variant, split) and ground truth (area, occupation) are
deliberately absent, so no scorer can read them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkerProfile:
    worker_id: str
    biography: str
    skills: tuple[str, ...]
    location: str | None
    availability: str | None
    rate_expectation: float | None  # KES per day


@dataclass(frozen=True)
class JobPosting:
    posting_id: str
    title: str
    description: str
    required_skills: tuple[str, ...]
    location: str | None
    availability: str | None
    budget: float | None  # KES per day


@dataclass(frozen=True)
class MatchedSkill:
    """A skill shared by worker and job, with how the worker came to have it.

    source: "listed" (the worker listed this ESCO skill), "text" (listed text outside ESCO),
    "informal_term" (inferred from an informal term the worker used) or "occupation_label"
    (inferred from an ESCO occupation named in the worker's text). graph_path holds the
    (source node, relation, target node) edges for inferred skills and is empty otherwise.
    """

    skill: str  # ESCO skill URI, or text:<normalised entry> for skills outside ESCO
    skill_label: str
    source: str
    graph_path: tuple[tuple[str, str, str], ...] = ()


@dataclass
class MatchScore:
    worker_id: str
    posting_id: str
    composite: float
    rule: float | None = None
    semantic: float | None = None
    components: dict[str, float] = field(default_factory=dict)  # per-criterion rule scores
    matched_skills: list[MatchedSkill] = field(default_factory=list)
    rank: int = 0
