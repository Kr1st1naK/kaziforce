"""
Explanation generation (FR-09).

Turns a completed match into statements a worker could check: the skills the two sides
share and how the worker came to have them, and the criteria that were actually assessed.
It reads a finished MatchScore and never feeds back into scoring or ranking, so producing
an explanation cannot change a score, a rank or any reported metric.

The coverage rules it supports are fixed in `docs/scoring-policy.md` §7, which was written
before this module existed.

See proposal Section 2.5 (Conceptual Framework) and Section 3.2.3.
"""

from __future__ import annotations

from kaziforce_api.data.models import JobPosting, MatchScore, MatchedSkill, WorkerProfile
from kaziforce_api.explainability.base import Explainer
from kaziforce_api.explainability.models import CRITERION, GRAPH_SKILL, LITERAL_SKILL, Explanation, Reason
from kaziforce_kg.graph import KnowledgeGraph

# How a trade is named to a worker. ESCO's occupation labels are job titles; these are the
# words the work is described in. An occupation not listed falls back to its own label.
TRADE_PHRASE = {
    "electrician": "electrical work",
    "plumber": "plumbing work",
    "carpenter": "carpentry",
    "bricklayer": "masonry work",
    "vehicle technician": "motor vehicle repair",
    "mobile phone repair technician": "phone repair",
    "tailor": "tailoring",
    "hairdresser": "hairdressing",
    "barber": "barbering",
    "laundry worker": "laundry work",
    "cook": "cooking",
}

INFERRED = ("informal_term", "occupation_label")

# Criteria that become a sentence of their own. skill_overlap is deliberately absent: it is
# the same evidence as the skill reasons, stated as a number instead of concretely, and
# counting it as well would count one fact twice.
CRITERION_PHRASE = {
    "location": "You're both in {value}.",
    "budget_fit": "Your rate of KES {rate} a day fits their budget.",
    "availability": "You can work {availability}, and that suits this job.",
}

NOT_ASSESSED_PHRASE = {
    ("location", True): "You haven't said where you work, so we couldn't check that.",
    ("location", False): "This job doesn't say where it is, so we couldn't check that.",
    ("budget_fit", True): "You haven't given a daily rate, so we couldn't compare it with their budget.",
    ("budget_fit", False): "This job doesn't give a budget, so we couldn't compare it with your rate.",
    ("availability", True): "You haven't said when you can work, so we couldn't check that.",
    ("availability", False): "This job doesn't say when the work is, so we couldn't check that.",
    ("skill_overlap", True): "You haven't listed any skills, so we couldn't compare them.",
    ("skill_overlap", False): "This job doesn't list the skills it needs, so we couldn't compare them.",
}


def trade_phrase(occupation: str) -> str:
    return TRADE_PHRASE.get(occupation.lower(), f"a {occupation}'s work")


class ExplanationGenerator(Explainer):
    """Builds an Explanation from a match, the two profiles and the knowledge graph.

    The graph is optional: without it, skills reached through it cannot be named, which is
    exactly what the knowledge-graph ablation configurations should show.
    """

    def __init__(self, graph: KnowledgeGraph | None = None):
        self.graph = graph

    def explain(self, worker: WorkerProfile, job: JobPosting, match: MatchScore) -> Explanation:
        reasons = [*self._skill_reasons(match), *self._criterion_reasons(worker, match)]
        return Explanation(
            worker_id=match.worker_id, posting_id=match.posting_id, rank=match.rank,
            reasons=tuple(reasons), not_assessed=self._not_assessed(worker, job, match),
            composite=match.composite, rule=match.rule, semantic=match.semantic,
        )

    # Skills

    def _skill_reasons(self, match: MatchScore) -> list[Reason]:
        """Graph-traced skills first, then the worker's own, in the order they were matched."""
        inferred = [s for s in match.matched_skills if s.source in INFERRED]
        literal = [s for s in match.matched_skills if s.source not in INFERRED]
        return [*(self._graph_reason(s) for s in inferred), *(self._literal_reason(s) for s in literal)]

    def _graph_reason(self, skill: MatchedSkill) -> Reason:
        occupation = self._occupation_of(skill)
        term = self._term_of(skill)
        phrase = trade_phrase(occupation) if occupation else "this trade"
        return Reason(
            kind=GRAPH_SKILL, text=f"{self._needs(skill)} That's part of {phrase}.",
            skill=skill.skill, skill_label=skill.skill_label, source=skill.source,
            occupation=occupation, term=term, graph_path=skill.graph_path,
        )

    def _literal_reason(self, skill: MatchedSkill) -> Reason:
        return Reason(
            kind=LITERAL_SKILL,
            text=f"You said you do {skill.skill_label}, and this job mentions it.",
            skill=skill.skill, skill_label=skill.skill_label, source=skill.source,
        )

    def _needs(self, skill: MatchedSkill) -> str:
        """ESCO splits skills from knowledge, and English needs the distinction: a job needs
        someone *to* install sockets, but simply needs electrical wiring plans."""
        if self._skill_type(skill.skill) == "knowledge":
            return f"This job needs {skill.skill_label}."
        return f"This job needs someone to {skill.skill_label}."

    def _skill_type(self, skill_id: str) -> str | None:
        if self.graph is None or skill_id not in self.graph.graph:
            return None
        return self.graph.graph.nodes[skill_id].get("skill_type")

    def _occupation_of(self, skill: MatchedSkill) -> str | None:
        """The occupation the skill was reached through: the target of the last-but-one edge."""
        for source, relation, target in skill.graph_path:
            if relation == "MAPS_TO":
                return self._label(target)
        return self._label(skill.graph_path[0][0]) if skill.graph_path else None

    def _term_of(self, skill: MatchedSkill) -> str | None:
        if skill.source != "informal_term" or not skill.graph_path:
            return None
        return self._label(skill.graph_path[0][0])

    def _label(self, node: str) -> str | None:
        if self.graph is None or node not in self.graph.graph:
            return None
        return self.graph.label(node)

    # Criteria

    @staticmethod
    def _criterion_reasons(worker: WorkerProfile, match: MatchScore) -> list[Reason]:
        """One sentence per criterion that was assessed and scored above zero.

        A criterion scored 0 is assessed and did not match; it is not a reason, and it is
        not reported as unassessed either.
        """
        reasons = []
        for criterion, template in CRITERION_PHRASE.items():
            score = match.components.get(criterion)
            if score is None or score <= 0:
                continue
            text = template.format(value=worker.location, rate=f"{worker.rate_expectation:,.0f}"
                                   if worker.rate_expectation is not None else "",
                                   availability=(worker.availability or "").lower())
            reasons.append(Reason(kind=CRITERION, text=text, criterion=criterion, score=score))
        return reasons

    @staticmethod
    def _not_assessed(worker: WorkerProfile, job: JobPosting, match: MatchScore) -> tuple[str, ...]:
        """Which criteria had nothing to compare, and which side was silent.

        Absent is not failure: it never counts towards coverage, and never against it.
        """
        missing = {
            "location": worker.location is None,
            "budget_fit": worker.rate_expectation is None,
            "availability": worker.availability is None,
            "skill_overlap": not worker.skills,
        }
        return tuple(NOT_ASSESSED_PHRASE[(criterion, missing[criterion])]
                     for criterion, score in match.components.items()
                     if score is None and criterion in missing)
