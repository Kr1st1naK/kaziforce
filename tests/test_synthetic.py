"""Synthetic data generator and loader round-trip (DR-05, DR-07)."""

import pandas as pd

from kaziforce_api.data.loaders import load_synthetic_data
from kaziforce_api.data.synthetic import AVAILABILITY, OCCUPATION_SPECS, generate_synthetic_data

WORKER_FIELDS = {"worker_id", "skills", "biography", "location", "availability", "rate_expectation"}
JOB_FIELDS = {"posting_id", "category", "required_skills", "description", "budget", "location"}


def test_generates_requested_counts_with_required_fields():
    data = generate_synthetic_data(n_workers=15, n_jobs=10)
    assert len(data["workers"]) == 15 and len(data["jobs"]) == 10
    assert WORKER_FIELDS <= set(data["workers"].columns)
    assert JOB_FIELDS <= set(data["jobs"].columns)
    assert data["workers"]["worker_id"].is_unique
    assert data["jobs"]["posting_id"].is_unique


def test_is_reproducible_for_a_seed():
    a = generate_synthetic_data(seed=7)
    b = generate_synthetic_data(seed=7)
    pd.testing.assert_frame_equal(a["workers"], b["workers"])
    pd.testing.assert_frame_equal(a["jobs"], b["jobs"])


def test_skills_come_from_specs_and_informal_terms_appear():
    data = generate_synthetic_data()
    esco = {s for spec in OCCUPATION_SPECS for s in spec.esco_skills}
    informal = {t for spec in OCCUPATION_SPECS for t in spec.informal_terms}
    worker_skills = {s for skills in data["workers"]["skills"] for s in skills}
    job_skills = {s for skills in data["jobs"]["required_skills"] for s in skills}
    assert worker_skills <= esco | informal
    assert job_skills <= esco
    assert worker_skills & informal, "expected some informal terms to exercise FR-03"
    assert set(data["workers"]["availability"]) <= set(AVAILABILITY)


def test_no_real_personal_identifiers():
    names = generate_synthetic_data()["workers"]["display_name"]
    assert names.str.fullmatch(r"Synthetic Worker \d{2}").all()


def test_loader_generates_saves_and_reloads(tmp_path):
    first = load_synthetic_data(tmp_path, n_workers=10, n_jobs=10)
    assert (tmp_path / "workers.csv").exists() and (tmp_path / "jobs.csv").exists()
    again = load_synthetic_data(tmp_path)
    assert again["workers"]["skills"].tolist() == first["workers"]["skills"].tolist()
    assert isinstance(again["jobs"]["required_skills"].iloc[0], list)
