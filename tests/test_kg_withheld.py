"""The withheld aliases (fundi wa stima -> electrician, mshonaji -> tailor) have no path into the built graph.

Stronger than the vocabulary-loader tests in test_vocabulary.py: these check the
graph itself, and every entry point a profile could use to reach it.
"""

import pytest

from kaziforce_api.data.data_loader import SPLITS, DataLoader
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.vocabulary import VocabularyExtension, normalize_alias

WITHHELD = {"fundi wa stima": "electrician", "mshonaji": "tailor"}
SURFACE_FORMS = ["fundi wa stima", "Fundi Wa Stima", "fundi stima", "mafundi wa stimu", "FUNDI-WA-STIMA!",
                 "fundi  wa\nstima", "mshonaji", "Mshonaji.", "MSHONAJI"]


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraphBuilder().build()


@pytest.fixture(scope="module")
def held_out_keys():
    return {t["normalized"] for t in VocabularyExtension().held_out_terms()}


@pytest.fixture(scope="module")
def profiles():
    loader = DataLoader()
    variants = loader.variants()
    workers = [w for s in SPLITS for w in loader.workers(s)]
    return {v: [w for w in workers if variants[w.worker_id] == v] for v in ("held_out", "known_alias")}


def test_the_frozen_vocabulary_withholds_exactly_these_two(held_out_keys):
    rows = VocabularyExtension().held_out_terms()
    assert {r["alias"] for r in rows} == set(WITHHELD)
    assert held_out_keys == {"fundi stima", "mshonaji"}


def test_no_node_id_or_string_attribute_contains_a_withheld_key(kg, held_out_keys):
    for node, data in kg.graph.nodes(data=True):
        strings = [node] + [v for v in data.values() if isinstance(v, str)]
        for s in strings:
            tokens = f" {normalize_alias(s)} "
            assert not [k for k in held_out_keys if f" {k} " in tokens], (node, s)


@pytest.mark.parametrize("form", SURFACE_FORMS)
def test_surface_forms_are_equivalent_to_a_withheld_key_and_match_nothing(kg, held_out_keys, form):
    assert normalize_alias(form) in held_out_keys
    assert kg.find_terms(form) == [] and kg.find_occupations(form) == [] and kg.skill_by_label(form) is None


def test_held_out_profiles_have_no_entry_point_into_the_graph(kg, profiles):
    held_out = profiles["held_out"]
    assert len(held_out) == 60
    for w in held_out:
        text = " ".join([w.biography, *w.skills])
        assert kg.find_terms(text) == [], w.biography
        assert kg.find_occupations(text) == [], w.biography
        assert all(kg.skill_by_label(s) is None for s in w.skills), w.skills


def test_positive_control_known_alias_profiles_do_enter_the_graph(kg, profiles):
    # Same templates and slot values as held_out, only the alias differs: if the matcher
    # were broken, the held-out test above would pass vacuously. This shows it is not.
    known = profiles["known_alias"]
    assert len(known) == 156
    for w in known:
        terms = kg.find_terms(" ".join([w.biography, *w.skills]))
        assert len(terms) == 1 and kg.label(terms[0]) == w.skills[0], w.biography


def test_withheld_occupations_are_still_in_the_graph_through_their_included_aliases(kg):
    # Withholding removes only the alias: electrician and tailor stay reachable via fundi wa umeme / fundi wa nguo.
    for alias, occupation in {"fundi wa umeme": "electrician", "fundi wa nguo": "tailor"}.items():
        (term,) = kg.find_terms(alias)
        assert kg.label(kg.occupation_of(term)) == occupation
