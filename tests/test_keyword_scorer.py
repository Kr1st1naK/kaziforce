"""KeywordScorer: BM25 with the frozen tokeniser of docs/scoring-policy.md §2."""

import math
import re
from pathlib import Path

import pytest

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, JobPosting, WorkerProfile
from kaziforce_api.matching.keyword import (
    ENGLISH_FUNCTION_WORDS, SWAHILI_FUNCTION_WORDS, KeywordScorer, token_list, tokens,
)
from kaziforce_kg.enrichment import NullEnricher

POLICY = Path(__file__).resolve().parents[1] / "docs" / "scoring-policy.md"


def _policy_list(heading: str) -> frozenset[str]:
    text = POLICY.read_text(encoding="utf-8")
    block = re.search(rf"{heading}:\n\n((?:    .+\n)+)", text).group(1)
    return frozenset(block.split())


def test_function_word_lists_equal_the_written_policy():
    assert ENGLISH_FUNCTION_WORDS == _policy_list("English function words")
    assert SWAHILI_FUNCTION_WORDS == _policy_list("Swahili function words")


@pytest.mark.parametrize("word", ["kazi", "miaka", "uzoefu", "experience", "available", "years", "rate", "day",
                                  "ksh", "kes", "fundi", "umeme", "nairobi"])
def test_content_words_are_kept_even_if_the_templates_use_them(word):
    assert word in tokens(word)


def test_tokeniser_rules():
    assert tokens("Mimi ni FUNDI wa umeme, niko Nairobi-Kasarani; 20 yrs.") == {"fundi", "umeme", "nairobi",
                                                                                 "kasarani", "yrs"}
    assert tokens("The plumber and an assistant") == {"plumber", "assistant"}
    assert tokens("") == frozenset()


def test_token_list_keeps_repeats_for_term_frequency():
    assert token_list("Pipes, pipes and the PIPES") == ["pipes", "pipes", "pipes"]
    assert frozenset(token_list("the pipe and a tap")) == tokens("the pipe and a tap")


def _job(pid, text):
    return JobPosting(pid, "", text, (), None, None, None)


def _enriched(bio, job):
    w = WorkerProfile("w", bio, (), None, None, None)
    e = NullEnricher()
    return EnrichedWorker(w, e.enrich(bio, ())), EnrichedJob(job, e.enrich(job.description, ()))


def test_bm25_matches_a_hand_computation():
    jobs = [_job("a", "pipe pipe tap"), _job("b", "wire socket"), _job("c", "pipe wire wire wire")]
    scorer = KeywordScorer(jobs)
    k1, b, avg = 1.2, 0.75, (3 + 2 + 4) / 3
    idf = {"pipe": math.log(1 + (3 - 2 + 0.5) / (2 + 0.5)), "tap": math.log(1 + (3 - 1 + 0.5) / (1 + 0.5))}

    def term(tf, length, t):
        return idf[t] * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / avg))

    w, a = _enriched("pipe tap", jobs[0])
    assert scorer.score(w, a) == pytest.approx(term(2, 3, "pipe") + term(1, 3, "tap"))
    _, b_job = _enriched("pipe tap", jobs[1])
    assert scorer.score(w, b_job) == 0.0


def test_rarer_terms_and_shorter_documents_score_higher():
    jobs = [_job("short", "plumber kisumu"), _job("long", "plumber kisumu " + " ".join(f"word{i}" for i in range(60))),
            _job("x", "plumber nairobi"), _job("y", "plumber mombasa")]
    scorer = KeywordScorer(jobs)
    w, short = _enriched("plumber kisumu", jobs[0])
    _, long = _enriched("plumber kisumu", jobs[1])
    assert scorer.score(w, short) > scorer.score(w, long) > 0
    w_common, _ = _enriched("plumber", jobs[0])
    w_rare, _ = _enriched("kisumu", jobs[0])
    assert scorer.score(w_rare, short) > scorer.score(w_common, short)


def test_query_terms_count_once_and_the_enrichment_is_ignored():
    jobs = [_job("a", "pipe tap"), _job("b", "wire")]
    scorer = KeywordScorer(jobs)
    once, a = _enriched("pipe", jobs[0])
    twice, _ = _enriched("pipe pipe pipe", jobs[0])
    assert scorer.score(once, a) == scorer.score(twice, a)
    other = EnrichedWorker(once.profile, NullEnricher().enrich("tap wire", ["tap", "wire"]))
    assert scorer.score(other, a) == scorer.score(once, a)


def test_unknown_posting_is_refused():
    scorer = KeywordScorer([_job("a", "pipe")])
    w, other = _enriched("pipe", _job("z", "pipe"))
    with pytest.raises(KeyError):
        scorer.score(w, other)
