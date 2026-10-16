"""ProfileEnricher and NullEnricher: interface, mapping, provenance, FR-10 and the withheld-alias condition."""

import inspect
import typing

import pytest

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.loaders import load_synthetic_ground_truth
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.enrichment import (
    INFERRED_SOURCES, INFORMAL_TERM, LISTED, OCCUPATION_LABEL, TEXT, Enricher, Enrichment, NullEnricher,
    ProfileEnricher, text_skill_id,
)
from kaziforce_kg.graph import HAS_ESSENTIAL_SKILL, MAPS_TO

ELECTRICIAN = "http://data.europa.eu/esco/occupation/4910419f-b4af-4f59-b544-9dbebc8a74f0"


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraphBuilder().build()


@pytest.fixture(scope="module")
def enricher(kg):
    return ProfileEnricher(kg)


@pytest.fixture(scope="module")
def dataset():
    loader = DataLoader()
    workers = {w.worker_id: w for w in loader.workers("development")}  # no validation or test rows
    truth = load_synthetic_ground_truth()["worker_truth"].set_index("worker_id")
    return workers, truth


# Interface (Chapter 4: both realise Enricher; configurations differ only in the object supplied)

def test_both_enrichers_realise_the_same_interface():
    for cls in (ProfileEnricher, NullEnricher):
        assert issubclass(cls, Enricher)
        assert inspect.signature(cls.enrich) == inspect.signature(Enricher.enrich)
        assert typing.get_type_hints(cls.enrich)["return"] is Enrichment
    assert inspect.isabstract(Enricher)


def test_both_return_an_enrichment(enricher):
    for e in (enricher, NullEnricher()):
        assert isinstance(e.enrich("Fundi wa umeme, Nyeri", ["fundi wa umeme"]), Enrichment)


# ProfileEnricher

def test_known_alias_maps_to_its_occupation_and_essential_skills(kg, enricher):
    e = enricher.enrich("Niko Nyeri, ni fundi wa umeme. Experience miaka 20.", ["fundi wa umeme"])
    assert [kg.label(t) for t in e.terms] == ["fundi wa umeme"] and e.occupations == (ELECTRICIAN,)
    assert e.inferred_skills == set(kg.skills_of(ELECTRICIAN)) and len(e.inferred_skills) == 21
    assert e.stated_skills == set() and e.unmapped == ()


def test_every_inferred_skill_carries_its_full_graph_path(kg, enricher):
    e = enricher.enrich("Mimi ni fundi wa umeme", ["fundi wa umeme"])
    (term,) = e.terms
    for ev in e.evidence:
        assert ev.source == INFORMAL_TERM
        assert ev.graph_path == ((term, MAPS_TO, ELECTRICIAN), (ELECTRICIAN, HAS_ESSENTIAL_SKILL, ev.skill))
        assert all(kg.graph.edges[u, v]["relation"] == r for u, r, v in ev.graph_path)
        assert ev.skill_label == kg.label(ev.skill)


def test_formal_profile_keeps_listed_skills_and_infers_the_rest(kg, enricher):
    listed = ["install electric switches", "splice cable"]
    e = enricher.enrich("Experienced electrician (20 years). Based in Nyeri.", listed)
    assert {ev.skill_label for ev in e.evidence if ev.source == LISTED} == set(listed)
    assert all(ev.graph_path == () for ev in e.evidence if ev.source == LISTED)
    inferred = [ev for ev in e.evidence if ev.source == OCCUPATION_LABEL]
    assert {ev.skill for ev in inferred} == set(kg.skills_of(ELECTRICIAN)) - e.stated_skills
    assert all(ev.graph_path == ((ELECTRICIAN, HAS_ESSENTIAL_SKILL, ev.skill),) for ev in inferred)


def test_listed_evidence_takes_precedence_and_each_skill_appears_once(enricher):
    e = enricher.enrich("fundi wa umeme", ["splice cable", "fundi wa umeme", "splice cable"])
    skills = [ev.skill for ev in e.evidence]
    assert len(skills) == len(set(skills)) == 21
    assert next(ev for ev in e.evidence if ev.skill_label == "splice cable").source == LISTED


def test_unmapped_entries_are_retained_as_text(enricher):
    e = enricher.enrich("Hello, I fix bicycles", ["bicycle repair", "Splice Cable"])
    assert e.unmapped == ("bicycle repair",)
    text = next(ev for ev in e.evidence if ev.source == TEXT)
    assert (text.skill, text.skill_label) == (text_skill_id("bicycle repair"), "bicycle repair")
    assert e.occupations == ()


def test_optional_skills_only_when_asked(kg):
    e = ProfileEnricher(kg, include_optional=True).enrich("fundi wa umeme", [])
    assert e.inferred_skills == set(kg.skills_of(ELECTRICIAN, essential_only=False))


# NullEnricher

def test_null_enricher_maps_nothing_and_keeps_every_entry_as_text():
    e = NullEnricher().enrich("Experienced electrician, fundi wa umeme", ["fundi wa umeme", "splice cable"])
    assert e.terms == () and e.occupations == () and e.inferred_skills == set()
    assert e.skills == {text_skill_id("fundi wa umeme"), text_skill_id("splice cable")}
    assert e.unmapped == ("fundi wa umeme", "splice cable")


# Withheld aliases at the enrichment level, with a positive control

def test_no_development_held_out_worker_enriches_to_an_occupation(enricher, dataset):
    workers, truth = dataset
    held_out = [w for wid, w in workers.items() if truth.loc[wid, "variant"] == "held_out"]
    assert len(held_out) == 24
    for w in held_out:
        e = enricher.enrich(w.biography, w.skills)
        assert e.terms == () and e.occupations == () and e.inferred_skills == set(), w.biography
        assert e.unmapped == (truth.loc[w.worker_id, "alias"],)


def test_positive_control_every_development_known_alias_worker_enriches_to_its_true_occupation(enricher, dataset):
    workers, truth = dataset
    known = [w for wid, w in workers.items() if truth.loc[wid, "variant"] == "known_alias"]
    assert len(known) == 64
    for w in known:
        e = enricher.enrich(w.biography, w.skills)
        assert e.occupations == (truth.loc[w.worker_id, "esco_uri"],), w.biography
        assert e.unmapped == () and all(ev.source in INFERRED_SOURCES for ev in e.evidence)


def test_held_out_and_known_alias_of_the_same_group_differ_only_in_the_mapping(enricher, dataset):
    workers, truth = dataset
    dev = truth[truth.index.isin(workers) & truth.variant.isin(["held_out", "known_alias"])]
    groups = dev.groupby("group_id")
    pairs = [g for _, g in groups if len(g) == 2]
    assert len(pairs) == 24
    for g in pairs:
        by_variant = dict(zip(g.variant, g.index))
        held, known = workers[by_variant["held_out"]], workers[by_variant["known_alias"]]
        assert enricher.enrich(held.biography, held.skills).occupations == ()
        assert enricher.enrich(known.biography, known.skills).occupations == (g.esco_uri.iloc[0],)
