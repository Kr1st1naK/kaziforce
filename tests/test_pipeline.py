"""Recommender and the configuration table: ranking, tie-breaking, and configurations as (enricher, scorer) pairs."""

import numpy as np
import pytest

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.models import JobPosting, MatchScore, WorkerProfile
from kaziforce_api.matching.base import Scorer
from kaziforce_api.matching.hybrid import HybridScorer
from kaziforce_api.matching.keyword import KeywordScorer
from kaziforce_api.matching.rule_based import RuleBasedScorer
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_api.pipeline import CONFIGURATIONS, KG_ABLATION_PAIRS, Recommender, build_recommender
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.enrichment import INFORMAL_TERM, Enricher, NullEnricher, ProfileEnricher


def _letters(texts):
    return np.array([[t.lower().count(c) for c in "abcdefghijklmnopqrstuvwxyz"] for t in texts], dtype=float) + 1e-3


class ConstantScorer(Scorer):
    def __init__(self, scores=None):
        self.scores = scores or {}

    def score_all(self, worker, jobs):
        return [MatchScore(worker.profile.worker_id, j.profile.posting_id, composite=self.scores.get(j.profile.posting_id, 0.0))
                for j in jobs]


JOBS = [JobPosting(pid, "", "", (), None, None, None) for pid in "abcdefgh"]
WORKER = WorkerProfile("w", "bio", (), None, None, None)


def test_ranks_by_descending_score_with_one_based_ranks():
    r = Recommender(NullEnricher(), ConstantScorer({"c": 0.9, "f": 0.5, "a": 0.7}), JOBS, k=3)
    top = r.rank(WORKER)
    assert [(m.posting_id, m.rank) for m in top] == [("c", 1), ("a", 2), ("f", 3)]


def test_k_handling():
    r = Recommender(NullEnricher(), ConstantScorer(), JOBS, k=3)
    assert len(r.rank(WORKER)) == 3 and len(r.rank(WORKER, k=5)) == 5 and len(r.rank(WORKER, k=0)) == len(JOBS)


def test_ties_follow_one_fixed_order_independent_of_input_order_and_scorer():
    a = [m.posting_id for m in Recommender(NullEnricher(), ConstantScorer(), JOBS).rank(WORKER, k=0)]
    b = [m.posting_id for m in Recommender(NullEnricher(), ConstantScorer(), JOBS[::-1]).rank(WORKER, k=0)]
    assert a == b and a != sorted(a)
    other_seed = [m.posting_id for m in Recommender(NullEnricher(), ConstantScorer(), JOBS, tie_break_seed=7).rank(WORKER, k=0)]
    assert other_seed != a


def test_every_configuration_is_an_enricher_scorer_pair():
    kg = KnowledgeGraphBuilder().build()
    semantic = SemanticScorer(encoder=_letters)
    expected = {"keyword": (NullEnricher, KeywordScorer), "rule_only": (NullEnricher, RuleBasedScorer),
                "rule_kg": (ProfileEnricher, RuleBasedScorer), "semantic_only": (NullEnricher, SemanticScorer),
                "semantic_kg": (ProfileEnricher, SemanticScorer), "hybrid_no_kg": (NullEnricher, HybridScorer),
                "full": (ProfileEnricher, HybridScorer)}
    assert set(CONFIGURATIONS) == set(expected)
    for name, (enricher_cls, scorer_cls) in expected.items():
        r = build_recommender(name, JOBS, kg=kg, semantic=semantic)
        assert type(r.enricher) is enricher_cls and type(r.scorer) is scorer_cls
        assert isinstance(r.enricher, Enricher) and isinstance(r.scorer, Scorer)


def test_kg_ablation_pairs_differ_only_in_the_enricher():
    kg, semantic = KnowledgeGraphBuilder().build(), SemanticScorer(encoder=_letters)
    for without, with_kg in KG_ABLATION_PAIRS:
        a, b = (build_recommender(n, JOBS, kg=kg, semantic=semantic) for n in (without, with_kg))
        assert type(a.scorer) is type(b.scorer)
        assert (type(a.enricher), type(b.enricher)) == (NullEnricher, ProfileEnricher)


def test_configuration_errors():
    with pytest.raises(ValueError, match="needs the knowledge graph"):
        build_recommender("full", JOBS)
    with pytest.raises(ValueError, match="unknown configuration"):
        build_recommender("bm25_plus", JOBS)


@pytest.fixture(scope="module")
def full_and_null():
    loader = DataLoader()
    jobs, kg, semantic = loader.jobs(), KnowledgeGraphBuilder().build(), SemanticScorer(encoder=_letters)
    return loader, {name: build_recommender(name, jobs, kg=kg, semantic=semantic) for name in ("full", "hybrid_no_kg")}


def test_full_configuration_ranks_all_280_jobs_for_a_development_worker(full_and_null):
    loader, recs = full_and_null
    worker = loader.worker("3917d39f-d0c0-46c2-aa34-9158711f68f3")  # known_alias, fundi wa umeme (worked example)
    ranking = recs["full"].rank(worker, k=0)
    assert len(ranking) == 280 and [m.rank for m in ranking] == list(range(1, 281))
    assert len({m.posting_id for m in ranking}) == 280
    assert all(0.0 <= m.composite <= 1.0 and m.rule is not None and m.semantic is not None for m in ranking)
    top = ranking[0]
    assert top.matched_skills and all(s.source == INFORMAL_TERM and s.graph_path for s in top.matched_skills)


def test_without_the_graph_the_same_worker_matches_no_skill(full_and_null):
    loader, recs = full_and_null
    worker = loader.worker("3917d39f-d0c0-46c2-aa34-9158711f68f3")
    assert all(not m.matched_skills for m in recs["hybrid_no_kg"].rank(worker, k=0))
