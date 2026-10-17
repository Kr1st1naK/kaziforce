"""
Keyword baseline: Okapi BM25 ranking of job postings for a worker's text, with
no knowledge graph and no embeddings.

The tokeniser is frozen in docs/scoring-policy.md §2, and FUNCTION_WORDS must
equal the lists given there (tests/test_keyword_scorer.py checks this).
Closed-class function words only; content words stay even when the generated
templates use them often. BM25 parameters are the standard defaults
(k1 = 1.2, b = 0.75), not tuned.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, JobPosting, MatchScore
from kaziforce_api.matching.base import Scorer

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


def token_list(text: str) -> list[str]:
    """Tokens in order, with repeats (for term frequencies)."""
    text = unicodedata.normalize("NFKC", text).lower()
    return [t for t in _TOKEN_RE.findall(text) if len(t) >= MIN_TOKEN_LENGTH and t not in FUNCTION_WORDS]


def tokens(text: str) -> frozenset[str]:
    return frozenset(token_list(text))


def worker_text(worker: EnrichedWorker) -> str:
    return " ".join([worker.profile.biography, *worker.profile.skills])


def job_text(job: JobPosting) -> str:
    return " ".join([job.title, job.description, *job.required_skills])


class KeywordScorer(Scorer):
    """Okapi BM25 over the candidate job postings. Reads only the profiles; the enrichment is ignored.

    The index (document frequencies, lengths) is built from the postings passed in, i.e. the
    candidate pool being ranked; no labels are involved. The worker text is the query, with each
    distinct query term counted once. IDF is ln(1 + (N - n + 0.5) / (n + 0.5)), which is never
    negative.
    """

    def __init__(self, jobs: Sequence[JobPosting], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self._tf = {j.posting_id: Counter(token_list(job_text(j))) for j in jobs}
        self._length = {pid: sum(tf.values()) for pid, tf in self._tf.items()}
        n_docs = len(self._tf)
        self._avg_length = sum(self._length.values()) / n_docs if n_docs else 0.0
        df = Counter(term for tf in self._tf.values() for term in tf)
        self._idf = {term: math.log(1 + (n_docs - n + 0.5) / (n + 0.5)) for term, n in df.items()}

    def score(self, worker: EnrichedWorker, job: EnrichedJob) -> float:
        pid = job.profile.posting_id
        if pid not in self._tf:
            raise KeyError(f"posting {pid} is not in the BM25 index")
        tf, length = self._tf[pid], self._length[pid]
        norm = self.k1 * (1 - self.b + self.b * length / self._avg_length) if self._avg_length else self.k1
        return sum(self._idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + norm) for t in tokens(worker_text(worker)) if t in tf)

    def score_all(self, worker: EnrichedWorker, jobs: Sequence[EnrichedJob]) -> list[MatchScore]:
        return [MatchScore(worker.profile.worker_id, j.profile.posting_id, composite=self.score(worker, j)) for j in jobs]
