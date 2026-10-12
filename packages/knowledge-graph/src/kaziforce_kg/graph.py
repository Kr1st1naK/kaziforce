"""
KnowledgeGraph: the typed, directed graph and its query interface (IR-04).

Node ids are ESCO URIs, except informal terms, which are "term:<normalised alias>".
Every node has `type` and `label`; every edge has `relation`. SCHEMA lists the
only (source type, relation, target type) triples the graph may contain.
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from kaziforce_kg.vocabulary import normalize_alias

OCCUPATION, SKILL, SKILL_GROUP, INFORMAL_TERM = "Occupation", "Skill", "SkillGroup", "InformalTerm"
NODE_TYPES = (OCCUPATION, SKILL, SKILL_GROUP, INFORMAL_TERM)

MAPS_TO, HAS_ESSENTIAL_SKILL, HAS_OPTIONAL_SKILL, TYPE_OF = (
    "MAPS_TO", "HAS_ESSENTIAL_SKILL", "HAS_OPTIONAL_SKILL", "TYPE_OF")
RELATIONS = (MAPS_TO, HAS_ESSENTIAL_SKILL, HAS_OPTIONAL_SKILL, TYPE_OF)

SCHEMA = {
    (INFORMAL_TERM, MAPS_TO, OCCUPATION),
    (OCCUPATION, HAS_ESSENTIAL_SKILL, SKILL),
    (OCCUPATION, HAS_OPTIONAL_SKILL, SKILL),
    (SKILL, TYPE_OF, SKILL_GROUP),
    (OCCUPATION, TYPE_OF, OCCUPATION),
}

Edge = tuple[str, str, str]  # (source, relation, target)


def term_id(normalized: str) -> str:
    return f"term:{normalized}"


class KnowledgeGraph:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self._terms = {d["normalized"]: n for n, d in graph.nodes(data=True) if d["type"] == INFORMAL_TERM}
        self._occupations = {normalize_alias(d["label"]): n for n, d in graph.nodes(data=True) if d["type"] == OCCUPATION}
        self._skills = {d["label"].casefold(): n for n, d in graph.nodes(data=True) if d["type"] == SKILL}

    # Lookup

    def find_terms(self, text: str) -> list[str]:
        """Informal-term nodes whose normalised alias occurs in the text as whole tokens (longest match first)."""
        return self._match(text, self._terms)

    def find_occupations(self, text: str) -> list[str]:
        """Occupation nodes whose ESCO preferred label occurs in the text as whole tokens."""
        return self._match(text, self._occupations)

    def skill_by_label(self, label: str) -> str | None:
        return self._skills.get(label.strip().casefold())

    # Traversal

    def occupation_of(self, term: str) -> str:
        return next(v for _, v, r in self.graph.out_edges(term, data="relation") if r == MAPS_TO)

    def skills_of(self, occupation: str, essential_only: bool = True) -> list[str]:
        wanted = {HAS_ESSENTIAL_SKILL} if essential_only else {HAS_ESSENTIAL_SKILL, HAS_OPTIONAL_SKILL}
        return sorted(v for _, v, r in self.graph.out_edges(occupation, data="relation") if r in wanted)

    def path(self, source: str, target: str) -> list[Edge]:
        """Shortest directed path as labelled edges; [] if there is none."""
        try:
            nodes = nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        return [(u, self.graph.edges[u, v]["relation"], v) for u, v in zip(nodes, nodes[1:])]

    # Description

    def label(self, node: str) -> str:
        return self.graph.nodes[node]["label"]

    def type(self, node: str) -> str:
        return self.graph.nodes[node]["type"]

    def stats(self) -> dict:
        nodes = Counter(d["type"] for _, d in self.graph.nodes(data=True))
        edges = Counter(r for _, _, r in self.graph.edges(data="relation"))
        triples = Counter((self.type(u), r, self.type(v)) for u, v, r in self.graph.edges(data="relation"))
        return {"nodes": {t: nodes.get(t, 0) for t in NODE_TYPES}, "edges": {r: edges.get(r, 0) for r in RELATIONS},
                "triples": {" ".join(t): n for t, n in sorted(triples.items())},
                "total_nodes": self.graph.number_of_nodes(), "total_edges": self.graph.number_of_edges()}

    @staticmethod
    def _match(text: str, index: dict[str, str]) -> list[str]:
        tokens = normalize_alias(text).split()
        longest = max((len(k.split()) for k in index), default=0)
        found, i = [], 0
        while i < len(tokens):
            for n in range(min(longest, len(tokens) - i), 0, -1):
                node = index.get(" ".join(tokens[i:i + n]))
                if node:
                    if node not in found:
                        found.append(node)
                    i += n
                    break
            else:
                i += 1
        return found
