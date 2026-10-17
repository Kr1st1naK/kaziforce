"""Synthetic dataset generator (kaziforce_api.data.synthetic), run on committed inputs only."""

import csv
import shutil
from pathlib import Path

import pandas as pd
import pytest

from kaziforce_api.data import synthetic
from kaziforce_api.data.loaders import load_synthetic_data, load_synthetic_ground_truth

ROOT = Path(__file__).resolve().parents[1]
VOCAB = ROOT / "data" / "vocabulary"
POOLS = ROOT / "data" / "raw" / "synthetic" / "inputs" / "area_skill_pools.csv"
SMALL = {"workers_per_area": 3, "area_overrides": {1: 5}, "jobs_per_area": 2}


def _build(out, **kw):
    return synthetic.build_dataset(out, VOCAB, POOLS, seed=7, **{**SMALL, **kw})


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    out = tmp_path_factory.mktemp("synthetic")
    manifest = _build(out)
    return out, manifest


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_counts_follow_parameters(small):
    out, manifest = small
    base = manifest["counts"]["base_workers_per_area"]
    assert base["1"] == 5 and all(n == 3 for a, n in base.items() if a != "1")
    assert all(n == 2 for n in manifest["counts"]["synthetic_jobs_per_area"].values())
    assert manifest["counts"]["jobs_per_source"] == {"synthetic": 20}  # no distractors without a corpus


def test_same_seed_gives_identical_files(small, tmp_path):
    out, _ = small
    _build(tmp_path)
    for name in ("workers.csv", "jobs.csv", "splits.csv", "manifest.json", "ground_truth/relevance.csv"):
        assert (out / name).read_bytes() == (tmp_path / name).read_bytes(), name


def test_splits_are_written_before_variants(tmp_path, monkeypatch):
    real = synthetic.make_variants

    def check_then_make(base, seed):
        assert (tmp_path / "splits.csv").exists(), "variants generated before splits.csv was written"
        return real(base, seed)

    monkeypatch.setattr(synthetic, "make_variants", check_then_make)
    _build(tmp_path)


def test_largest_remainder_allocation():
    assert synthetic._allocate(12, synthetic.SPLITS) == {"development": 5, "validation": 2, "test": 5}
    assert synthetic._allocate(30, synthetic.SPLITS) == {"development": 12, "validation": 6, "test": 12}


def test_known_alias_and_held_out_differ_only_in_alias(small):
    out, _ = small
    workers = pd.read_csv(out / "workers.csv", dtype=str)
    truth = pd.read_csv(out / "ground_truth" / "worker_truth.csv", dtype=str).set_index("worker_id")
    held = workers[workers.variant == "held_out"]
    assert len(held)
    for _, h in held.iterrows():
        k = workers[(workers.group_id == h.group_id) & (workers.variant == "known_alias")].iloc[0]
        known_alias, held_alias = truth.loc[k.worker_id, "alias"], truth.loc[h.worker_id, "alias"]
        swap = h.biography.replace(held_alias, known_alias).replace(held_alias.capitalize(), known_alias.capitalize())
        assert swap == k.biography
        assert (h.location, h.availability, h.rate_expectation) == (k.location, k.availability, k.rate_expectation)


def test_edited_compatibility_matrix_is_respected(tmp_path):
    _build(tmp_path)
    matrix = tmp_path / "ground_truth" / "compatibility_matrix.csv"
    rows = _read(matrix)
    for r in rows:  # make Tailor workers also relevant to Laundry jobs
        if r["worker_area_id"] == "11" and r["job_area_id"] == "15":
            r["relevant"] = "1"
    synthetic._write(matrix, rows, list(rows[0]))
    _build(tmp_path)
    gt = load_synthetic_ground_truth(tmp_path)
    pairs = gt["relevance"].merge(gt["worker_truth"], on="worker_id").merge(
        gt["job_truth"], on="posting_id", suffixes=("_w", "_j"))
    assert {(11, 15), (11, 11)} <= set(zip(pairs.area_id_w, pairs.area_id_j))


def test_missing_known_alias_stops_generation(tmp_path):
    vocab = tmp_path / "vocab"
    shutil.copytree(VOCAB, vocab)
    rows = _read(vocab / "aliases.csv")
    for r in rows:
        if r["alias"] == "mwashi":
            r["status"] = "pending_review"
    synthetic._write(vocab / "aliases.csv", rows, list(rows[0]))
    with pytest.raises(ValueError, match="bricklayer"):
        synthetic.load_inputs(vocab, POOLS)


def test_loader_returns_profile_files_with_lists(small):
    out, _ = small
    data = load_synthetic_data(out)
    assert isinstance(data["workers"]["skills"].iloc[0], list)
    assert isinstance(data["jobs"]["required_skills"].iloc[0], list)
