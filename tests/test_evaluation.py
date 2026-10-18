"""Evaluator and run folder: development-split guard, aggregation, recorded metadata."""

import csv
import json

import numpy as np
import pytest

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.evaluation.evaluator import ALL, EVALUATION_SPLITS, Evaluator
from kaziforce_api.evaluation.report import write_run
from kaziforce_api.matching.semantic import SemanticScorer
from kaziforce_api.pipeline import KG_ABLATION_PAIRS, build_recommender
from kaziforce_kg.builder import KnowledgeGraphBuilder


def _letters(texts):
    return np.array([[t.lower().count(c) for c in "abcdefghijklmnopqrstuvwxyz"] for t in texts], dtype=float) + 1e-3


@pytest.fixture(scope="module")
def run():
    loader = DataLoader()
    jobs, kg, semantic = loader.jobs(), KnowledgeGraphBuilder().build(), SemanticScorer(encoder=_letters)
    names = ("keyword", "rule_only", "rule_kg", "full")
    recommenders = {n: build_recommender(n, jobs, kg=kg, semantic=semantic) for n in names}
    return loader, Evaluator(loader, recommenders, max_queries=12).run()


@pytest.mark.parametrize("split", ["validation", "test", "train"])
def test_only_the_development_split_may_be_evaluated(split):
    assert EVALUATION_SPLITS == ("development",)
    with pytest.raises(ValueError, match="may not be evaluated"):
        Evaluator(DataLoader(), {}, split=split)


def test_every_query_is_a_development_worker(run):
    loader, result = run
    split_of = loader.split_of()
    assert {split_of[q.worker_id] for q in result.queries} == {"development"}
    assert len(result.queries) == 4 * 12


def test_summary_is_the_macro_mean_of_the_queries(run):
    _, result = run
    rows = {(r["configuration"], r["variant"]): r for r in result.summary()}
    for config in result.configurations:
        qs = [q for q in result.queries if q.configuration == config]
        assert rows[(config, ALL)]["queries"] == 12
        assert rows[(config, ALL)]["MRR"] == pytest.approx(sum(q.reciprocal_rank for q in qs) / len(qs))
        assert rows[(config, ALL)]["P@5"] == pytest.approx(sum(q.precision[5] for q in qs) / len(qs))
        variant_n = sum(r["queries"] for (c, v), r in rows.items() if c == config and v != ALL)
        assert variant_n == 12
    assert all(q.first_relevant_rank and 1 <= q.first_relevant_rank <= 273 for q in result.queries)


def test_run_folder_records_code_and_data_versions(run, tmp_path):
    _, result = run
    meta = {"git": {"commit": "a" * 40, "uncommitted_changes": False}, "seed": 42, "startup_seconds": 1.0,
            "machine": {"platform": "test", "processor": "test", "python": "3.12"}}
    out = write_run(result, meta, tmp_path / "run", ablation_pairs=[p for p in KG_ABLATION_PAIRS if p[0] == "rule_only"])
    assert {p.name for p in out.iterdir()} == {"metrics.md", "metrics.csv", "per_query.csv", "run.json"}
    assert json.loads((out / "run.json").read_text()) == meta
    with open(out / "per_query.csv", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == len(result.queries)
    md = (out / "metrics.md").read_text()
    assert "rule_only → rule_kg" in md and "random ranking (expected)" in md and "aaaaaaa" in md
    with pytest.raises(FileExistsError):
        write_run(result, meta, out)  # a run folder is never overwritten
