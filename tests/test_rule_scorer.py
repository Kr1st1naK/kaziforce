"""RuleBasedScorer: the criteria and the missing-field rule of docs/scoring-policy.md §1."""

import pytest

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, JobPosting, WorkerProfile
from kaziforce_api.matching.rule_based import (
    RuleBasedScorer, RuleBasedWeights, availability_match, budget_fit, combine_present, location_match, skill_overlap,
)
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.enrichment import INFORMAL_TERM, LISTED, NullEnricher, ProfileEnricher


@pytest.fixture(scope="module")
def kg_enricher():
    return ProfileEnricher(KnowledgeGraphBuilder().build())


def worker(bio="Mimi ni fundi wa umeme", skills=("fundi wa umeme",), location="Nairobi - Kasarani",
           availability="Part-time", rate=2000.0):
    return WorkerProfile("w", bio, tuple(skills), location, availability, rate)


def job(skills=("install electricity sockets", "splice cable", "bind wire", "electricity"),
        location="Nairobi - Kasarani", availability="Part-time", budget=2500.0, description="Rewire a shop"):
    return JobPosting("j", "Rewire a shop", description, tuple(skills), location, availability, budget)


def enriched(enricher, w: WorkerProfile, j: JobPosting):
    return (EnrichedWorker(w, enricher.enrich(w.biography, w.skills)),
            EnrichedJob(j, enricher.enrich(j.description, j.required_skills)))


# Criteria

def test_skill_overlap_is_coverage_of_the_job_requirements():
    assert skill_overlap(frozenset("abc"), frozenset("ab")) == 1.0
    assert skill_overlap(frozenset("a"), frozenset("abcd")) == 0.25
    assert skill_overlap(frozenset(), frozenset("ab")) is None and skill_overlap(frozenset("a"), frozenset()) is None


@pytest.mark.parametrize("a, b, expected", [
    ("Nairobi - Kasarani", "nairobi - kasarani ", 1.0), ("Nairobi - Kasarani", "Nairobi - Embakasi", 0.5),
    ("Kisumu", "Nakuru", 0.0), ("Nairobi - Kibera", "Kisumu", 0.0), (None, "Kisumu", None), ("Kisumu", "", None),
])
def test_location(a, b, expected):
    assert location_match(a, b) == expected


@pytest.mark.parametrize("rate, budget, expected", [
    (2000, 2500, 1.0), (2500, 2500, 1.0), (3000, 2000, 0.5), (4000, 2000, 0.0), (5000, 2000, 0.0),
    (None, 2000, None), (2000, None, None), (2000, 0, None),
])
def test_budget_fit(rate, budget, expected):
    assert budget_fit(rate, budget) == expected


@pytest.mark.parametrize("w, j, expected", [
    ("Part-time", "Part-time", 1.0), ("Full-time", "Weekends", 1.0), ("Weekends", "Full-time", 0.0),
    ("Part-time", "Weekends", 0.0), (None, "Weekends", None), ("Full-time", None, None),
])
def test_availability(w, j, expected):
    assert availability_match(w, j) == expected


def test_renormalisation_drops_absent_criteria():
    weights = RuleBasedWeights().by_criterion()
    all_present = {"skill_overlap": 0.5, "location": 1.0, "budget_fit": 1.0, "availability": 0.0}
    assert combine_present(all_present, weights) == pytest.approx(0.4 * 0.5 + 0.2 + 0.2 + 0.0)
    skill_only = {"skill_overlap": 0.5, "location": None, "budget_fit": None, "availability": None}
    assert combine_present(skill_only, weights) == pytest.approx(0.5)
    minimal = {"skill_overlap": 0.5, "location": 1.0, "budget_fit": None, "availability": None}
    assert combine_present(minimal, weights) == pytest.approx((0.4 * 0.5 + 0.2 * 1.0) / 0.6)
    assert combine_present(dict.fromkeys(weights), weights) == 0.0


# Scorer on enriched profiles

def test_known_alias_worker_matches_through_the_graph(kg_enricher):
    w, j = enriched(kg_enricher, worker(), job())
    r = RuleBasedScorer().score(w, j)
    assert r.components == {"skill_overlap": 1.0, "location": 1.0, "budget_fit": 1.0, "availability": 1.0}
    assert r.score == pytest.approx(1.0)
    assert [m.skill_label for m in r.matched_skills] == list(job().required_skills)
    assert all(m.source == INFORMAL_TERM and len(m.graph_path) == 2 for m in r.matched_skills)


def test_without_the_graph_the_alias_matches_no_skill():
    w, j = enriched(NullEnricher(), worker(), job())
    r = RuleBasedScorer().score(w, j)
    assert r.components["skill_overlap"] == 0.0 and r.matched_skills == ()
    assert r.score == pytest.approx((0.2 + 0.2 + 0.2) / 1.0)


def test_listed_skills_match_literally_without_the_graph():
    w, j = enriched(NullEnricher(), worker(skills=("splice cable", "bind wire")), job())
    r = RuleBasedScorer().score(w, j)
    assert r.components["skill_overlap"] == 0.5
    assert [m.skill_label for m in r.matched_skills] == ["splice cable", "bind wire"]


def test_listed_esco_skill_is_reported_as_listed(kg_enricher):
    w, j = enriched(kg_enricher, worker(bio="Skilled in wiring", skills=("splice cable",)), job())
    (m,) = RuleBasedScorer().score(w, j).matched_skills
    assert (m.skill_label, m.source, m.graph_path) == ("splice cable", LISTED, ())


def test_job_side_inference_does_not_inflate_requirements(kg_enricher):
    # The description names the occupation, but J is the job's stated skills only.
    w, j = enriched(kg_enricher, worker(skills=("splice cable",), bio="I splice cables"),
                    job(description="We need an electrician"))
    assert RuleBasedScorer().score(w, j).components["skill_overlap"] == 0.25


def test_distractor_is_scored_on_skills_alone(kg_enricher):
    w, j = enriched(kg_enricher, worker(), job(skills=("Excel", "Payroll"), location=None, availability=None, budget=None))
    r = RuleBasedScorer().score(w, j)
    assert r.components == {"skill_overlap": 0.0, "location": None, "budget_fit": None, "availability": None}
    assert r.score == 0.0


def test_minimal_worker_is_scored_on_skills_and_location(kg_enricher):
    w, j = enriched(kg_enricher, worker(bio="Fundi wa umeme - Nairobi - Kasarani", availability=None, rate=None), job())
    r = RuleBasedScorer().score(w, j)
    assert r.components["availability"] is None and r.components["budget_fit"] is None
    assert r.score == pytest.approx((0.4 * 1.0 + 0.2 * 1.0) / 0.6)


def test_weights_held_by_the_scorer_and_overridable_per_call(kg_enricher):
    w, j = enriched(kg_enricher, worker(availability="Weekends"), job())
    skills_only = RuleBasedWeights(skill_overlap=1, location=0, budget=0, availability=0)
    assert RuleBasedScorer(skills_only).score(w, j).score == pytest.approx(1.0)
    default = RuleBasedScorer()
    assert default.score(w, j).score == pytest.approx(0.8)
    assert default.score(w, j, weights=skills_only).score == pytest.approx(1.0)
    assert default.score(w, j).score == pytest.approx(0.8)


def test_invalid_weights_are_refused():
    with pytest.raises(ValueError):
        RuleBasedScorer(RuleBasedWeights(0, 0, 0, 0))
    with pytest.raises(ValueError):
        RuleBasedScorer(RuleBasedWeights(skill_overlap=-0.1))


def test_scores_stay_in_the_unit_interval(kg_enricher):
    scorer = RuleBasedScorer()
    for rate in (500, 2500, 9000):
        for loc in ("Nairobi - Kasarani", "Nairobi - Umoja", "Kisumu", None):
            w, j = enriched(kg_enricher, worker(rate=rate, location=loc), job())
            assert 0.0 <= scorer.score(w, j).score <= 1.0
