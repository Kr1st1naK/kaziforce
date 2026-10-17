"""SemanticScorer (docs/scoring-policy.md §3), with a stub encoder; one slow test loads the real model."""

import numpy as np
import pytest

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, JobPosting, WorkerProfile
from kaziforce_api.matching.semantic import MODEL_NAME, MODEL_REVISION, SemanticScorer, job_text, worker_text
from kaziforce_kg.builder import KnowledgeGraphBuilder
from kaziforce_kg.enrichment import NullEnricher, ProfileEnricher

VECTORS = {"a": [1.0, 0.0], "b": [0.0, 2.0], "c": [-1.0, 0.0], "d": [1.0, 1.0]}


class StubEncoder:
    """Maps each text to a fixed vector (by its first character) and counts what it was asked to encode."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        return np.array([VECTORS[t[0]] for t in texts])


def pair(bio, description, skills=(), enricher=None):
    enricher = enricher or NullEnricher()
    w = WorkerProfile("w", bio, tuple(skills), None, None, None)
    j = JobPosting(description, "", description, (), None, None, None)
    return EnrichedWorker(w, enricher.enrich(bio, skills)), EnrichedJob(j, enricher.enrich(description, ()))


def test_cosine_similarity_with_clipping():
    scorer = SemanticScorer(encoder=StubEncoder())
    w, _ = pair("a worker", "x")
    jobs = [pair("a", d)[1] for d in ("a job", "b job", "c job", "d job")]
    assert scorer.score_many(w, jobs) == pytest.approx([1.0, 0.0, 0.0, 1 / np.sqrt(2)])  # c is -1, clipped to 0
    assert scorer.score(w, jobs[3]) == pytest.approx(1 / np.sqrt(2))


def test_each_distinct_text_is_encoded_once():
    encoder = StubEncoder()
    scorer = SemanticScorer(encoder=encoder)
    jobs = [pair("a", d)[1] for d in ("b one", "d two")]
    for bio in ("a first", "a first", "d other"):
        scorer.score_many(pair(bio, "x")[0], jobs)
    encoded = [t for call in encoder.calls for t in call]
    assert sorted(encoded) == ["a first", "b one", "d other", "d two"] and scorer.encoded == 4


def test_worker_text_appends_enrichment_labels_and_job_text_is_the_description():
    kg_pair = pair("Mimi ni fundi wa umeme", "Rewire a shop", ["fundi wa umeme"], ProfileEnricher(KnowledgeGraphBuilder().build()))
    text = worker_text(kg_pair[0])
    assert text.startswith("Mimi ni fundi wa umeme Skills: ") and "install electricity sockets" in text
    null_pair = pair("Mimi ni fundi wa umeme", "Rewire a shop", ["fundi wa umeme"])
    assert worker_text(null_pair[0]) == "Mimi ni fundi wa umeme Skills: fundi wa umeme."
    assert worker_text(pair("Hello", "x")[0]) == "Hello"
    assert job_text(kg_pair[1]) == "Rewire a shop"


def test_no_model_is_loaded_when_an_encoder_is_injected():
    scorer = SemanticScorer(encoder=StubEncoder())
    scorer.score(*pair("a", "b"))
    assert scorer.info() == {"model": MODEL_NAME, "revision": MODEL_REVISION, "cached_texts": 2, "encoder": "injected"}


@pytest.mark.slow
def test_real_model_ranks_a_related_job_above_an_unrelated_one():
    scorer = SemanticScorer()
    w, wiring = pair("Electrician with ten years of house wiring experience", "Install sockets and rewire a house")
    _, payroll = pair("x", "Manage payroll and quarterly financial reports")
    related, unrelated = scorer.score_many(w, [wiring, payroll])
    assert 0.0 <= unrelated < related <= 1.0
    assert scorer.embed(["test"]).shape == (1, 384)
