"""KnowledgeGraphBuilder and the KnowledgeGraph query interface, on the committed inputs."""

import csv
import shutil
from pathlib import Path

import networkx as nx
import pytest

from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.graph import (
    HAS_ESSENTIAL_SKILL, INFORMAL_TERM, MAPS_TO, NODE_TYPES, OCCUPATION, SCHEMA, KnowledgeGraph, term_id,
)
from kaziforce_kg.vocabulary import VocabularyExtension

ROOT = Path(__file__).resolve().parents[1]
ALIASES = ROOT / "data" / "vocabulary" / "aliases.csv"
ELECTRICIAN = "http://data.europa.eu/esco/occupation/4910419f-b4af-4f59-b544-9dbebc8a74f0"


@pytest.fixture(scope="module")
def kg() -> KnowledgeGraph:
    return KnowledgeGraphBuilder().build()


def test_graph_is_directed_and_typed(kg):
    g = kg.graph
    assert isinstance(g, nx.DiGraph) and not isinstance(g, nx.MultiDiGraph)
    assert all(d["type"] in NODE_TYPES and d["label"] for _, d in g.nodes(data=True))
    assert all((g.nodes[u]["type"], r, g.nodes[v]["type"]) in SCHEMA for u, v, r in g.edges(data="relation"))


def test_counts_match_the_inputs(kg):
    s = kg.stats()
    assert s["nodes"] == {"Occupation": 11, "Skill": 379, "SkillGroup": 140, "InformalTerm": 14}
    assert s["edges"] == {"MAPS_TO": 14, "HAS_ESSENTIAL_SKILL": 234, "HAS_OPTIONAL_SKILL": 273, "TYPE_OF": 380}
    assert (s["total_nodes"], s["total_edges"]) == (544, 901)


def test_every_included_alias_maps_to_its_esco_occupation(kg):
    vocab = VocabularyExtension(ALIASES)
    for t in vocab.kg_terms():
        node = term_id(t["normalized"])
        out = [(v, r) for _, v, r in kg.graph.out_edges(node, data="relation")]
        assert out == [(t["esco_uri"], MAPS_TO)], t["alias"]
        assert kg.graph.in_degree(node) == 0


def test_no_area_attribute_anywhere(kg):
    assert not any("area" in key for _, d in kg.graph.nodes(data=True) for key in d)


@pytest.mark.parametrize("text, expected", [
    ("Niko Nyeri, ni fundi wa umeme. Experience miaka 20", ["fundi wa umeme"]),
    ("MAFUNDI WA UMEME!", ["fundi wa umeme"]),
    ("Kinyozi hapa Thika", ["kinyozi"]),
    ("Mama fua, dobi, Kasarani", ["mama fua", "dobi"]),
    ("mpishiii au mpishi", ["mpishi"]),
    ("fundi tu", []),
])
def test_find_terms_matches_whole_normalised_tokens(kg, text, expected):
    assert [kg.label(t) for t in kg.find_terms(text)] == expected


def test_find_occupations_uses_whole_words(kg):
    found = kg.find_occupations("Experienced electrician and mobile phone repair technician")
    assert [kg.label(o) for o in found] == ["electrician", "mobile phone repair technician"]
    assert kg.find_occupations("electricians and cooking") == []


def test_traversal_from_alias_to_skill(kg):
    term = kg.find_terms("fundi wa umeme")[0]
    assert kg.occupation_of(term) == ELECTRICIAN
    essential = kg.skills_of(ELECTRICIAN)
    assert len(essential) == 21 and len(kg.skills_of(ELECTRICIAN, essential_only=False)) == 52
    skill = kg.skill_by_label("Install Electricity Sockets ")
    assert skill in essential
    assert kg.path(term, skill) == [(term, MAPS_TO, ELECTRICIAN), (ELECTRICIAN, HAS_ESSENTIAL_SKILL, skill)]
    assert kg.path(skill, term) == [] and kg.path("missing", term) == []


def test_barber_is_a_type_of_hairdresser(kg):
    barber = next(n for n, d in kg.graph.nodes(data=True) if d["type"] == OCCUPATION and d["label"] == "barber")
    assert [kg.label(v) for v in kg.graph.successors(barber)
            if kg.type(v) == OCCUPATION] == ["hairdresser"]


def _aliases_copy(tmp_path, edit):
    path = tmp_path / "aliases.csv"
    with open(ALIASES, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows, fields = list(reader), reader.fieldnames
    edit(rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def test_builder_refuses_an_alias_mapped_outside_the_graph(tmp_path):
    def edit(rows):
        next(r for r in rows if r["alias"] == "fundi bomba")["esco_uri"] = "http://example.org/not-in-graph"
    with pytest.raises(ValueError, match="unknown node"):
        KnowledgeGraphBuilder(VocabularyExtension(_aliases_copy(tmp_path, edit))).build()


def test_builder_refuses_a_held_out_alias_that_reaches_the_graph_as_a_label(tmp_path):
    kg_dir = tmp_path / "kg"
    shutil.copytree(ROOT / "data" / "kg", kg_dir)
    groups = (kg_dir / "skill_groups.csv").read_text(encoding="utf-8").splitlines()
    groups[1] = groups[1].split(",")[0] + ",Fundi wa Stima,esco_skill_group,default"
    (kg_dir / "skill_groups.csv").write_text("\n".join(groups) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="held-out alias"):
        KnowledgeGraphBuilder(kg_dir=kg_dir).build()


def test_informal_terms_are_the_only_term_nodes(kg):
    terms = {d["alias"] for _, d in kg.graph.nodes(data=True) if d["type"] == INFORMAL_TERM}
    assert terms == {t["alias"] for t in VocabularyExtension(ALIASES).kg_terms()}
