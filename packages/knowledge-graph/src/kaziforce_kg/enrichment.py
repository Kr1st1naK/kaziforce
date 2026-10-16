"""
Profile enrichment: links a worker or job profile to the knowledge graph before
scoring, and feeds both scorers (conceptual framework, proposal Section 2.5).

Both enrichers realise the same Enricher interface and return the same
Enrichment type, so the knowledge-graph and no-knowledge-graph configurations
differ only in which object is supplied, never in conditional logic inside the
scorers.

Skill identifiers in an Enrichment are ESCO skill URIs, or "text:<normalised
entry>" for listed skills that are not mapped to the graph (kept for literal
matching; FR-10). Every skill carries the evidence that produced it, including
the full graph path for inferred skills.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from kaziforce_kg.graph import MAPS_TO, Edge, KnowledgeGraph
from kaziforce_kg.vocabulary import normalize_alias

# Evidence sources. "Stated" skills come from the profile itself; "inferred" ones from the graph.
LISTED = "listed"                   # skills entry equal to an ESCO skill label
TEXT = "text"                       # skills entry not mapped to the graph, kept as literal text
INFORMAL_TERM = "informal_term"     # informal term -> occupation -> skill
OCCUPATION_LABEL = "occupation_label"  # ESCO occupation label in the text -> skill
STATED_SOURCES = (LISTED, TEXT)
INFERRED_SOURCES = (INFORMAL_TERM, OCCUPATION_LABEL)


def text_skill_id(entry: str) -> str:
    return f"text:{normalize_alias(entry)}"


@dataclass(frozen=True)
class SkillEvidence:
    skill: str                      # ESCO skill URI or text:<normalised entry>
    skill_label: str
    source: str                     # listed, text, informal_term or occupation_label
    graph_path: tuple[Edge, ...] = ()  # full graph path for inferred skills; () for stated ones


@dataclass(frozen=True)
class Enrichment:
    terms: tuple[str, ...]          # informal-term nodes matched
    occupations: tuple[str, ...]    # occupation nodes reached
    evidence: tuple[SkillEvidence, ...]  # one entry per skill, in discovery order
    unmapped: tuple[str, ...]       # listed entries not mapped to the graph, original text (FR-10)

    @property
    def skills(self) -> frozenset[str]:
        return frozenset(e.skill for e in self.evidence)

    @property
    def stated_skills(self) -> frozenset[str]:
        return frozenset(e.skill for e in self.evidence if e.source in STATED_SOURCES)

    @property
    def inferred_skills(self) -> frozenset[str]:
        return frozenset(e.skill for e in self.evidence if e.source in INFERRED_SOURCES)

    def labels(self) -> list[str]:
        return [e.skill_label for e in self.evidence]


class Enricher(ABC):
    @abstractmethod
    def enrich(self, text: str, skills: Sequence[str]) -> Enrichment:
        """Enrich one profile: free text (biography or description) and its listed skills."""


class ProfileEnricher(Enricher):
    """Knowledge-graph enrichment.

    1. Listed skills equal to an ESCO skill label -> that skill (listed).
    2. Informal terms in the text or the listed skills -> MAPS_TO occupation -> its essential
       skills (informal_term), with the full path.
    3. ESCO occupation labels in the text -> the occupation's essential skills (occupation_label).
    4. Any other listed entry stays as literal text (text) and is reported as unmapped.
    A skill reached more than once keeps its first evidence, in the order above.
    """

    def __init__(self, kg: KnowledgeGraph, include_optional: bool = False):
        self.kg = kg
        self.include_optional = include_optional

    def enrich(self, text: str, skills: Sequence[str]) -> Enrichment:
        evidence: dict[str, SkillEvidence] = {}
        unmapped: list[str] = []
        terms: list[str] = []

        for entry in skills:
            skill = self.kg.skill_by_label(entry)
            if skill:
                evidence.setdefault(skill, SkillEvidence(skill, self.kg.label(skill), LISTED))
            else:
                found = self.kg.find_terms(entry)
                terms += [t for t in found if t not in terms]
                if not found:
                    unmapped.append(entry)
        terms += [t for t in self.kg.find_terms(text) if t not in terms]

        occupations: list[str] = []
        for term in terms:
            occupation = self.kg.occupation_of(term)
            if occupation not in occupations:
                occupations.append(occupation)
            self._infer(evidence, occupation, INFORMAL_TERM, ((term, MAPS_TO, occupation),))
        for occupation in self.kg.find_occupations(text):
            if occupation not in occupations:
                occupations.append(occupation)
            self._infer(evidence, occupation, OCCUPATION_LABEL, ())

        for entry in unmapped:
            evidence.setdefault(text_skill_id(entry), SkillEvidence(text_skill_id(entry), entry, TEXT))
        return Enrichment(tuple(terms), tuple(occupations), tuple(evidence.values()), tuple(unmapped))

    def _infer(self, evidence: dict, occupation: str, source: str, prefix: tuple[Edge, ...]) -> None:
        for skill in self.kg.skills_of(occupation, essential_only=not self.include_optional):
            relation = self.kg.graph.edges[occupation, skill]["relation"]
            evidence.setdefault(skill, SkillEvidence(skill, self.kg.label(skill), source,
                                                     prefix + ((occupation, relation, skill),)))


class NullEnricher(Enricher):
    """No knowledge graph: every listed skill is kept as literal text; nothing is mapped or inferred."""

    def enrich(self, text: str, skills: Sequence[str]) -> Enrichment:
        evidence: dict[str, SkillEvidence] = {}
        for entry in skills:
            evidence.setdefault(text_skill_id(entry), SkillEvidence(text_skill_id(entry), entry, TEXT))
        return Enrichment((), (), tuple(evidence.values()), tuple(skills))
