"""KeywordScorer: the frozen tokeniser of docs/scoring-policy.md §2."""

import re
from pathlib import Path

import pytest

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, JobPosting, WorkerProfile
from kaziforce_api.matching.keyword import (
    ENGLISH_FUNCTION_WORDS, SWAHILI_FUNCTION_WORDS, KeywordScorer, jaccard, tokens,
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


def test_jaccard():
    assert jaccard(frozenset("ab"), frozenset("bc")) == pytest.approx(1 / 3)
    assert jaccard(frozenset(), frozenset()) == 0.0


def _pair(bio, skills, title, description, required):
    w = WorkerProfile("w", bio, tuple(skills), "Kisumu", None, None)
    j = JobPosting("j", title, description, tuple(required), "Kisumu", None, None)
    e = NullEnricher()
    return EnrichedWorker(w, e.enrich(bio, skills)), EnrichedJob(j, e.enrich(description, required))


def test_score_uses_profile_text_only_and_penalises_length():
    w, short = _pair("Plumber in Kisumu", ["fix leaking pipes"], "Repair leaking pipes", "Plumber needed in Kisumu",
                     ["fix leaking pipes"])
    _, long = _pair("Plumber in Kisumu", ["fix leaking pipes"], "Analyst",
                    "plumber kisumu " + " ".join(f"word{i}" for i in range(200)), ["excel"])
    scorer = KeywordScorer()
    assert scorer.score(w, short) > scorer.score(w, long) > 0
