"""DataLoader and domain models on the committed synthetic dataset."""

import dataclasses
from collections import Counter

import pytest

from kaziforce_api.data.data_loader import SPLITS, DataLoader
from kaziforce_api.data.models import JobPosting, WorkerProfile


@pytest.fixture(scope="module")
def loader():
    return DataLoader()


def test_split_sizes_match_the_manifest(loader):
    expected = loader.manifest()["counts"]["worker_rows_per_split"]
    assert {s: len(loader.workers(s)) for s in SPLITS} == expected


def test_development_split_variant_counts(loader):
    variants = loader.variants()
    dev = Counter(variants[w.worker_id] for w in loader.workers("development"))
    assert dev == {"formal": 64, "known_alias": 64, "held_out": 24, "minimal": 64}


def test_profiles_expose_no_bookkeeping_or_labels():
    banned = {"group_id", "variant", "split", "area", "area_id", "occupation", "esco_uri", "relevant"}
    for cls in (WorkerProfile, JobPosting):
        assert not banned & {f.name for f in dataclasses.fields(cls)}


def test_missing_fields_become_none(loader):
    variants = loader.variants()
    for w in loader.workers("development"):
        if variants[w.worker_id] == "minimal":
            assert w.availability is None and w.rate_expectation is None and w.location
        else:
            assert w.availability and isinstance(w.rate_expectation, float)
    distractors = [j for j in loader.jobs() if j.budget is None]
    assert len(distractors) == 200
    assert all(j.location is None and j.availability is None and j.required_skills for j in distractors)


def test_jobs_and_relevance(loader):
    jobs = loader.jobs()
    assert len(jobs) == 280 and len({j.posting_id for j in jobs}) == 280
    relevance = loader.relevance()
    assert len(relevance) == 4224
    per_worker = Counter(w for w, _ in relevance)
    assert set(per_worker.values()) == {8}


def test_worker_lookup_is_restricted_to_the_split(loader):
    dev = loader.workers("development")[0]
    assert loader.worker(dev.worker_id) == dev
    test_id = loader.workers("test")[0].worker_id
    with pytest.raises(KeyError):
        loader.worker(test_id, "development")


def test_unknown_split_is_refused(loader):
    with pytest.raises(ValueError):
        loader.workers("train")


def test_missing_dataset_raises_and_writes_nothing(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataLoader(tmp_path).workers()
    assert not any(tmp_path.iterdir())
