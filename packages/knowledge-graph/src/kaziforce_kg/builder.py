"""
KnowledgeGraphBuilder: builds the enriched knowledge graph as a typed nx.DiGraph.

Population sequence (proposal Section 3.2.3):
  1. ESCO backbone from data/kg/ (scripts/build_kg_inputs.py): the 11 selected
     occupations, their essential and optional skills, and one hop of the skill
     hierarchy (skill groups and ISCED-F fields).
  2. Kenya vocabulary extension: accepted, kg_included=yes aliases only, each
     MAPS_TO its ESCO occupation. Held-out aliases never enter the graph.

Occupational areas are deliberately not nodes: area is the evaluation label
space, so no scorer may reach it through the graph. Worker and job profiles are
not nodes either; they are linked to the graph by enrichment
(kaziforce_kg.enrichment).
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import networkx as nx

from kaziforce_kg.graph import (
    HAS_ESSENTIAL_SKILL, HAS_OPTIONAL_SKILL, INFORMAL_TERM, MAPS_TO, NODE_TYPES, OCCUPATION, SCHEMA, SKILL,
    SKILL_GROUP, TYPE_OF, KnowledgeGraph, term_id,
)
from kaziforce_kg.vocabulary import VocabularyExtension, normalize_alias

SKILL_RELATIONS = {"essential": HAS_ESSENTIAL_SKILL, "optional": HAS_OPTIONAL_SKILL}


def _default_kg_dir() -> Path:
    override = os.getenv("KAZIFORCE_DATA_DIR")
    if override:
        return Path(override).resolve() / "kg"
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "kg" / "manifest.json").exists():
            return parent / "data" / "kg"
    raise FileNotFoundError("data/kg/ not found; set KAZIFORCE_DATA_DIR or run scripts/build_kg_inputs.py.")


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class KnowledgeGraphBuilder:
    def __init__(self, vocabulary: VocabularyExtension | None = None, kg_dir: Path | None = None):
        self.vocabulary = vocabulary or VocabularyExtension()
        self.kg_dir = Path(kg_dir) if kg_dir else _default_kg_dir()

    def build(self) -> KnowledgeGraph:
        g = nx.DiGraph()
        d = self.kg_dir
        for o in _read(d / "occupations.csv"):
            g.add_node(o["uri"], type=OCCUPATION, label=o["label"], isco_code=o["isco_code"])
        for s in _read(d / "skills.csv"):
            g.add_node(s["uri"], type=SKILL, label=s["label"], skill_type=s["skill_type"], reuse_level=s["reuse_level"])
        for s in _read(d / "skill_groups.csv"):
            g.add_node(s["uri"], type=SKILL_GROUP, label=s["label"], scheme=s["scheme"])

        for r in _read(d / "occupation_skills.csv"):
            self._edge(g, r["occupation_uri"], SKILL_RELATIONS[r["relation"]], r["skill_uri"])
        for r in _read(d / "skill_broader.csv"):
            self._edge(g, r["skill_uri"], TYPE_OF, r["broader_uri"])
        for r in _read(d / "occupation_broader.csv"):
            self._edge(g, r["occupation_uri"], TYPE_OF, r["broader_uri"])

        for t in self.vocabulary.kg_terms():
            node = term_id(t["normalized"])
            if node in g and g.nodes[node]["alias"] != t["alias"]:
                raise ValueError(f"aliases {g.nodes[node]['alias']!r} and {t['alias']!r} share the key {t['normalized']!r}")
            g.add_node(node, type=INFORMAL_TERM, label=t["alias"], alias=t["alias"], normalized=t["normalized"],
                       language=t["language"], register=t["register"])
            self._edge(g, node, MAPS_TO, t["esco_uri"])

        self._validate(g)
        return KnowledgeGraph(g)

    @staticmethod
    def _edge(g: nx.DiGraph, source: str, relation: str, target: str) -> None:
        for node in (source, target):
            if node not in g:
                raise ValueError(f"{relation} edge refers to unknown node {node}")
        g.add_edge(source, target, relation=relation)

    def _validate(self, g: nx.DiGraph) -> None:
        for n, data in g.nodes(data=True):
            if data.get("type") not in NODE_TYPES or not data.get("label"):
                raise ValueError(f"node {n} has no valid type or label")
        for u, v, r in g.edges(data="relation"):
            if (g.nodes[u]["type"], r, g.nodes[v]["type"]) not in SCHEMA:
                raise ValueError(f"edge {u} -{r}-> {v} is not in the schema")
        held_out = {t["normalized"] for t in self.vocabulary.held_out_terms()}
        for n, data in g.nodes(data=True):
            keys = {normalize_alias(data["label"]), data.get("normalized", "")}
            if keys & held_out:
                raise ValueError(f"held-out alias reached the graph as node {n}")
