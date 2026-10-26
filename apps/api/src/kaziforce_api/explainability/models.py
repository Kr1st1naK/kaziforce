"""What an explanation is made of.

A Reason is one concrete, attributable, checkable statement: something the worker could
verify about themselves. The coverage rules of `docs/scoring-policy.md` §7 are properties
of this object, so the definition lives in one place and the evaluator cannot drift from
the API.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Reason kinds, in descending strength.
GRAPH_SKILL = "graph_skill"          # a skill reached through the knowledge graph
LITERAL_SKILL = "literal_skill"      # a skill the worker listed, or their own words
CRITERION = "criterion"              # an assessed rule criterion that scored above zero

SKILL_KINDS = (GRAPH_SKILL, LITERAL_SKILL)


@dataclass(frozen=True)
class Reason:
    """One statement, with the evidence it was drawn from."""

    kind: str
    text: str
    skill: str | None = None
    skill_label: str | None = None
    source: str | None = None
    occupation: str | None = None
    term: str | None = None
    criterion: str | None = None
    score: float | None = None
    graph_path: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class Explanation:
    """Why one posting was recommended to one worker."""

    worker_id: str
    posting_id: str
    rank: int
    reasons: tuple[Reason, ...] = ()
    not_assessed: tuple[str, ...] = ()
    composite: float = 0.0
    rule: float | None = None
    semantic: float | None = None

    # Coverage (docs/scoring-policy.md §7). Computed from the reasons, never from the
    # score, the rank or the display band.

    @property
    def covered(self) -> bool:
        """The NFR-02 rule: at least one shared skill, graph-traced or literal."""
        return any(r.kind in SKILL_KINDS for r in self.reasons)

    @property
    def covered_inclusive(self) -> bool:
        """Reported alongside: any concrete reason at all, including a criterion."""
        return bool(self.reasons)

    @property
    def covered_graph(self) -> bool:
        """Reported alongside: at least one skill reached through the knowledge graph."""
        return any(r.kind == GRAPH_SKILL for r in self.reasons)

    @property
    def text(self) -> tuple[str, ...]:
        """The explanation as readable sentences, strongest reason first."""
        return tuple(r.text for r in self.reasons)

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "posting_id": self.posting_id,
            "rank": self.rank,
            "scores": {"composite": self.composite, "rule": self.rule, "semantic": self.semantic},
            "reasons": [_reason_dict(r) for r in self.reasons],
            "not_assessed": list(self.not_assessed),
            "covered": self.covered,
        }


def _reason_dict(reason: Reason) -> dict:
    """Only the fields this kind of reason actually carries, so the JSON stays readable."""
    out: dict = {"kind": reason.kind, "text": reason.text}
    for name in ("skill", "skill_label", "source", "occupation", "term", "criterion", "score"):
        value = getattr(reason, name)
        if value is not None:
            out[name] = value
    if reason.graph_path:
        out["graph_path"] = [list(edge) for edge in reason.graph_path]
    return out
