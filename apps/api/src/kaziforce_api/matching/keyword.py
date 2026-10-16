"""
Keyword baseline: token overlap between worker and job text, with no knowledge
graph and no embeddings.

The tokeniser is frozen in docs/scoring-policy.md §2, and FUNCTION_WORDS must
equal the lists given there (tests/test_keyword_scorer.py checks this).
Closed-class function words only; content words stay even when the generated
templates use them often.
"""

from __future__ import annotations

import re
import unicodedata

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker

ENGLISH_FUNCTION_WORDS = frozenset("""
about above after again against all also although among and any are because been before being below
between both but can cannot could did does doing down during each either few for from further had has
have having her here hers herself him himself his how into its itself may might more most must myself
neither nor not off once only other ought our ours ourselves out over own per same shall she should some
such than that the their theirs them themselves then there these they this those through too under until
upon very via was were what when where which while who whom whose why will with within without would yet
you your yours yourself yourselves
""".split())
SWAHILI_FUNCTION_WORDS = frozenset("""
mimi wewe yeye sisi nyinyi ninyi wao yangu yako yake yetu yenu wangu wake wetu wenu zangu zako zake
huyu huyo yule hawa hao wale hii hiyo ile hizi hizo zile kwa katika kwenye kutoka hadi pia lakini ama
kama ili bila tena sana niko uko yuko tuko mko nina una ana tuna mna ndiyo siyo hapa pale huko
""".split())
FUNCTION_WORDS = ENGLISH_FUNCTION_WORDS | SWAHILI_FUNCTION_WORDS
MIN_TOKEN_LENGTH = 3
_TOKEN_RE = re.compile(r"[a-z]+")


def tokens(text: str) -> frozenset[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    return frozenset(t for t in _TOKEN_RE.findall(text) if len(t) >= MIN_TOKEN_LENGTH and t not in FUNCTION_WORDS)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


class KeywordScorer:
    """Jaccard similarity of the token sets. Reads only the profiles; the enrichment is ignored."""

    def score(self, worker: EnrichedWorker, job: EnrichedJob) -> float:
        w, j = worker.profile, job.profile
        return jaccard(tokens(" ".join([w.biography, *w.skills])),
                       tokens(" ".join([j.title, j.description, *j.required_skills])))
