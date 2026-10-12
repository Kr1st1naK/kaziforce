"""The committed synthetic dataset in data/raw/synthetic/ (frozen; regenerate with
scripts/build_synthetic_dataset.py and re-run these tests)."""

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

from kaziforce_api.data.synthetic import sha256_file
from kaziforce_kg.vocabulary import load_kg_vocabulary, normalize_alias

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "synthetic"
VOCAB = ROOT / "data" / "vocabulary"
INFORMAL = {"known_alias", "held_out", "minimal"}
BANNED_PROFILE_COLUMNS = {"area", "area_id", "occupation", "esco_uri", "esco_label", "isco_code", "relevant",
                          "relevance", "label", "split", "category", "alias"}


@pytest.fixture(scope="module")
def d():
    workers = pd.read_csv(DATA / "workers.csv", dtype=str, keep_default_na=False)
    jobs = pd.read_csv(DATA / "jobs.csv", dtype=str, keep_default_na=False)
    for df, col in ((workers, "skills"), (jobs, "required_skills")):
        df[col] = df[col].apply(json.loads)
    gt = DATA / "ground_truth"
    return {
        "workers": workers, "jobs": jobs,
        "splits": pd.read_csv(DATA / "splits.csv", dtype=str),
        "worker_truth": pd.read_csv(gt / "worker_truth.csv", dtype=str, keep_default_na=False),
        "job_truth": pd.read_csv(gt / "job_truth.csv", dtype=str, keep_default_na=False),
        "relevance": pd.read_csv(gt / "relevance.csv", dtype=str),
        "matrix": pd.read_csv(gt / "compatibility_matrix.csv", dtype=str),
        "pools": pd.read_csv(DATA / "inputs" / "area_skill_pools.csv", dtype=str),
        "aliases": pd.read_csv(VOCAB / "aliases.csv", dtype=str, keep_default_na=False),
        "manifest": json.loads((DATA / "manifest.json").read_text(encoding="utf-8")),
    }


def test_no_group_spans_two_splits(d):
    per_group = d["worker_truth"].groupby("group_id")["split"].nunique()
    assert (per_group == 1).all()
    splits = dict(zip(d["splits"].group_id, d["splits"].split))
    assert set(d["workers"].group_id) == set(splits)
    assert all(splits[g] == s for g, s in zip(d["worker_truth"].group_id, d["worker_truth"].split))


def test_profile_files_have_no_label_or_occupation_columns(d):
    assert not BANNED_PROFILE_COLUMNS & set(d["workers"].columns)
    assert not BANNED_PROFILE_COLUMNS & set(d["jobs"].columns)


def test_held_out_aliases_only_in_held_out_variants_of_electrician_and_tailor(d):
    held = d["aliases"][(d["aliases"].status == "accepted") & (d["aliases"].kg_included == "no")]
    held_keys = {normalize_alias(a) for a in held.alias}
    assert held_keys, "expected held-out aliases in the frozen vocabulary"
    truth = d["worker_truth"].set_index("worker_id")
    for _, w in d["workers"].iterrows():
        text = normalize_alias(w.biography + " " + " ".join(w.skills))
        if any(re.search(rf"\b{re.escape(k)}\b", text) for k in held_keys):
            assert w.variant == "held_out", w.biography
            assert truth.loc[w.worker_id, "area_id"] in {"1", "11"}
    assert set(truth[truth.variant == "held_out"].area_id) == {"1", "11"}
    kg_keys = {r["normalized"] for r in load_kg_vocabulary(VOCAB / "aliases.csv")}
    assert not held_keys & kg_keys


def test_informal_variants_contain_no_formal_labels(d):
    skill_labels = {s.lower() for s in d["pools"].skill_label}
    occupation_labels = {s.lower() for s in d["pools"].esco_label}
    aliases = set(d["aliases"][d["aliases"].status == "accepted"].alias)
    informal = d["workers"][d["workers"].variant.isin(INFORMAL)]
    assert len(informal)
    for _, w in informal.iterrows():
        bio = w.biography.lower()
        assert not [s for s in skill_labels if s in bio], w.biography
        assert not [o for o in occupation_labels if re.search(rf"\b{re.escape(o)}\b", bio)], w.biography
        assert set(w.skills) <= aliases and len(w.skills) == 1


def test_formal_variants_use_esco_skill_labels(d):
    labels = set(d["pools"].skill_label)
    formal = d["workers"][d["workers"].variant == "formal"]
    assert all(set(s) <= labels and 4 <= len(s) <= 8 for s in formal.skills)


def test_no_exact_duplicate_bios(d):
    assert not d["workers"].biography.duplicated().any()


def test_counts_match_manifest(d):
    c = d["manifest"]["counts"]
    truth = d["worker_truth"]
    assert c["worker_rows"] == len(d["workers"]) == len(truth)
    assert c["worker_rows_per_variant"] == dict(Counter(truth.variant))
    assert c["worker_rows_per_split"] == dict(Counter(truth.split))
    assert c["groups_per_split"] == dict(Counter(d["splits"].split))
    assert c["base_workers_per_area"] == dict(Counter(truth.drop_duplicates("group_id").area_id))
    assert c["jobs"] == len(d["jobs"]) and c["jobs_per_source"] == dict(Counter(d["jobs"].source))
    assert c["relevance_pairs"] == len(d["relevance"])


def test_manifest_records_the_frozen_vocabulary(d):
    sha = d["manifest"]["inputs_sha256"]
    assert sha["aliases.csv"] == sha256_file(VOCAB / "aliases.csv")
    assert sha["area_esco_map.csv"] == sha256_file(VOCAB / "area_esco_map.csv")
    assert sha["area_skill_pools.csv"] == sha256_file(DATA / "inputs" / "area_skill_pools.csv")
    assert sha["compatibility_matrix.csv"] == sha256_file(DATA / "ground_truth" / "compatibility_matrix.csv")
    assert all(n >= 8 for k, n in d["manifest"]["templates"].items() if k != "job")


def test_relevance_follows_the_compatibility_matrix(d):
    ok = {(r.worker_area_id, r.job_area_id) for r in d["matrix"].itertuples() if r.relevant == "1"}
    w_area = dict(zip(d["worker_truth"].worker_id, d["worker_truth"].area_id))
    j_area = dict(zip(d["job_truth"].posting_id, d["job_truth"].area_id))
    expected = {(w, j) for w in w_area for j in j_area if j_area[j] and (w_area[w], j_area[j]) in ok}
    assert expected == set(zip(d["relevance"].worker_id, d["relevance"].posting_id))


def test_every_worker_has_relevant_jobs_and_distractors_never_relevant(d):
    assert set(d["relevance"].worker_id) == set(d["workers"].worker_id)
    distractors = set(d["job_truth"][d["job_truth"].source == "job_skill_set"].posting_id)
    assert not distractors & set(d["relevance"].posting_id)


def test_distractors_are_cleaned_and_contain_no_contact_details(d):
    js = d["jobs"][d["jobs"].source == "job_skill_set"]
    assert len(js) == d["manifest"]["parameters"]["n_distractors"]
    contact = re.compile(r"@\w|https?://|www\.|\(\d{3}\)\s?\d{3}-\d{4}|\b\d{3}-\d{3}-\d{4}\b")
    assert not js.description.str.contains(contact).any()
    assert not js.description.str.contains(r"[A-Z]{12,}").any()  # upper-case blocks were lowercased


def test_synthetic_jobs_use_esco_labels(d):
    labels = set(d["pools"].skill_label)
    syn = d["jobs"][d["jobs"].source == "synthetic"]
    assert all(set(s) <= labels and 3 <= len(s) <= 5 for s in syn.required_skills)
