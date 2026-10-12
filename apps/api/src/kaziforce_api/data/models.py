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
    """A skill shared by worker and job, with the KG path that gave it to the worker."""

    skill: str  # ESCO skill URI, or normalised text for skills outside ESCO
    label: str
    path: tuple[tuple[str, str, str], ...] = ()  # (source, relation, target) edges; empty if asserted


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
