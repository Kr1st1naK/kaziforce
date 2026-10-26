"""
The explanation generator (FR-09) and the coverage rules it supports (NFR-02).

The rules are fixed in docs/scoring-policy.md §7, which was committed before this module
existed. These tests hold the code to that document: a shared skill is required for
coverage, a criterion match alone is not enough, a similarity number never counts, and an
absent criterion counts neither for nor against.
"""

from __future__ import annotations

import pytest

from kaziforce_api.data.models import JobPosting, MatchScore, MatchedSkill, WorkerProfile
from kaziforce_api.explainability.explain import ExplanationGenerator, trade_phrase
from kaziforce_api.explainability.models import CRITERION, GRAPH_SKILL, LITERAL_SKILL

TERM = "term:fundi umeme"
OCCUPATION = "http://data.europa.eu/esco/occupation/electrician"
SOCKETS = "http://data.europa.eu/esco/skill/sockets"
PLANS = "http://data.europa.eu/esco/skill/plans"

VIA_TERM = ((TERM, "MAPS_TO", OCCUPATION), (OCCUPATION, "HAS_ESSENTIAL_SKILL", SOCKETS))
VIA_OCCUPATION = ((OCCUPATION, "HAS_ESSENTIAL_SKILL", SOCKETS),)


class FakeGraph:
    """Only what the generator asks of a graph: labels and the ESCO skill/knowledge split."""

    def __init__(self):
        import networkx as nx
        self.graph = nx.DiGraph()
        self.graph.add_node(TERM, label="fundi wa umeme", type="InformalTerm")
        self.graph.add_node(OCCUPATION, label="electrician", type="Occupation")
        self.graph.add_node(SOCKETS, label="install electricity sockets", type="Skill", skill_type="skill")
        self.graph.add_node(PLANS, label="electrical wiring plans", type="Skill", skill_type="knowledge")

    def label(self, node: str) -> str:
        return self.graph.nodes[node]["label"]


@pytest.fixture
def generator():
    return ExplanationGenerator(FakeGraph())


def worker(**kw) -> WorkerProfile:
    fields = {"worker_id": "w-1", "biography": "Mimi ni fundi wa umeme.", "skills": ("fundi wa umeme",),
              "location": "Nyeri", "availability": "Full-time", "rate_expectation": 2500.0}
    return WorkerProfile(**{**fields, **kw})


def job(**kw) -> JobPosting:
    fields = {"posting_id": "j-1", "title": "Rewire a shop", "description": "Rewire a small shop.",
              "required_skills": ("install electricity sockets",), "location": "Nyeri",
              "availability": "Full-time", "budget": 3000.0}
    return JobPosting(**{**fields, **kw})


def skill(**kw) -> MatchedSkill:
    fields = {"skill": SOCKETS, "skill_label": "install electricity sockets",
              "source": "informal_term", "graph_path": VIA_TERM}
    return MatchedSkill(**{**fields, **kw})


def match(**kw) -> MatchScore:
    fields = {"worker_id": "w-1", "posting_id": "j-1", "composite": 0.84, "rule": 0.82, "semantic": 0.74,
              "components": {"skill_overlap": 1.0, "location": 1.0, "budget_fit": 1.0, "availability": 1.0},
              "matched_skills": [skill()], "rank": 1}
    return MatchScore(**{**fields, **kw})


# The coverage rules

def test_a_shared_skill_covers_the_recommendation(generator):
    assert generator.explain(worker(), job(), match()).covered


def test_a_criterion_match_alone_does_not_cover_it(generator):
    """The strict rule: a posting sharing no skill is not one we can claim to explain."""
    explanation = generator.explain(worker(), job(), match(matched_skills=[], components={
        "skill_overlap": 0.0, "location": 1.0, "budget_fit": 1.0, "availability": 1.0}))
    assert not explanation.covered
    assert explanation.covered_inclusive          # it is still a reason, and reported as one
    assert not explanation.covered_graph
    assert explanation.text == ("You're both in Nyeri.",
                                "Your rate of KES 2,500 a day fits their budget.",
                                "You can work full-time, and that suits this job.")


def test_a_semantic_score_alone_never_counts(generator):
    """A cosine value is a number, not something a worker can check."""
    explanation = generator.explain(worker(), job(), match(
        rule=None, semantic=0.91, components={}, matched_skills=[]))
    assert not explanation.covered
    assert not explanation.covered_inclusive
    assert explanation.text == ()


def test_a_listed_skill_covers_it_but_is_not_graph_traced(generator):
    explanation = generator.explain(worker(), job(), match(
        matched_skills=[skill(source="listed", graph_path=())]))
    assert explanation.covered and not explanation.covered_graph
    assert explanation.reasons[0].kind == LITERAL_SKILL


def test_an_absent_criterion_counts_neither_way(generator):
    """Absent is not failure. It is reported separately and changes no coverage flag."""
    explanation = generator.explain(worker(rate_expectation=None), job(), match(components={
        "skill_overlap": 1.0, "location": 1.0, "budget_fit": None, "availability": 1.0}))
    assert explanation.covered
    assert "You haven't given a daily rate, so we couldn't compare it with their budget." in explanation.not_assessed
    assert not any("budget" in r.text for r in explanation.reasons)


def test_a_criterion_scored_zero_is_neither_a_reason_nor_unassessed(generator):
    """Assessed and different is a real 0; it is not a reason, and it is not missing either."""
    explanation = generator.explain(worker(location="Thika"), job(), match(components={
        "skill_overlap": 1.0, "location": 0.0, "budget_fit": 1.0, "availability": 1.0}))
    assert not any(r.criterion == "location" for r in explanation.reasons)
    assert not any("where" in line for line in explanation.not_assessed)


# The sentences

def test_a_skill_and_a_knowledge_item_are_phrased_differently(generator):
    """ESCO splits skills from knowledge, and English needs the distinction."""
    explanation = generator.explain(worker(), job(), match(matched_skills=[
        skill(), skill(skill=PLANS, skill_label="electrical wiring plans", graph_path=(
            (TERM, "MAPS_TO", OCCUPATION), (OCCUPATION, "HAS_ESSENTIAL_SKILL", PLANS)))]))
    assert explanation.text[0] == "This job needs someone to install electricity sockets. That's part of electrical work."
    assert explanation.text[1] == "This job needs electrical wiring plans. That's part of electrical work."


def test_a_graph_reason_names_the_term_and_the_occupation_it_went_through(generator):
    reason = generator.explain(worker(), job(), match()).reasons[0]
    assert reason.kind == GRAPH_SKILL
    assert reason.term == "fundi wa umeme" and reason.occupation == "electrician"
    assert reason.graph_path == VIA_TERM


def test_a_skill_reached_from_an_occupation_label_has_no_term(generator):
    reason = generator.explain(worker(), job(), match(matched_skills=[
        skill(source="occupation_label", graph_path=VIA_OCCUPATION)])).reasons[0]
    assert reason.kind == GRAPH_SKILL and reason.occupation == "electrician" and reason.term is None


def test_graph_traced_skills_are_stated_before_the_worker_s_own(generator):
    explanation = generator.explain(worker(), job(), match(matched_skills=[
        skill(source="listed", skill_label="breaker box repair", graph_path=()), skill()]))
    assert [r.kind for r in explanation.reasons][:2] == [GRAPH_SKILL, LITERAL_SKILL]


def test_criteria_come_after_skills(generator):
    kinds = [r.kind for r in generator.explain(worker(), job(), match()).reasons]
    assert kinds[0] == GRAPH_SKILL and set(kinds[1:]) == {CRITERION}


def test_a_trade_outside_the_phrase_list_falls_back_to_its_own_label():
    assert trade_phrase("electrician") == "electrical work"
    assert trade_phrase("welder") == "a welder's work"


# Separability (NFR-03)

def test_the_generator_works_without_a_graph():
    """The knowledge-graph ablation configurations have no graph; the generator must not need one."""
    explanation = ExplanationGenerator(None).explain(worker(), job(), match(
        matched_skills=[skill(source="listed", graph_path=())]))
    assert explanation.covered
    assert explanation.reasons[0].text == "You said you do install electricity sockets, and this job mentions it."


def test_explaining_does_not_touch_the_match(generator):
    """The generator reads a finished match; it must not be able to change a score or a rank."""
    original = match()
    before = (original.composite, original.rule, original.semantic, original.rank,
              dict(original.components), list(original.matched_skills))
    generator.explain(worker(), job(), original)
    assert (original.composite, original.rule, original.semantic, original.rank,
            dict(original.components), list(original.matched_skills)) == before


def test_the_structured_form_carries_the_evidence(generator):
    payload = generator.explain(worker(), job(), match()).to_dict()
    assert payload["covered"] is True
    first = payload["reasons"][0]
    assert first["kind"] == GRAPH_SKILL and first["occupation"] == "electrician"
    assert first["graph_path"][0] == [TERM, "MAPS_TO", OCCUPATION]
    assert "score" not in first  # a graph reason carries no criterion score
