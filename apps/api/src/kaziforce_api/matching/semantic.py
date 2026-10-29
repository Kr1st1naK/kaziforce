"""
Semantic similarity matching component (docs/scoring-policy.md §3).

Embeds the worker text (biography, then the labels of the skills in the
worker's enrichment) and the job description with a pre-trained
sentence-transformer, all-MiniLM-L6-v2 at a pinned revision, and compares
them by cosine similarity clipped to [0, 1]. The same text rule applies in
every configuration; only the enrichment's contents differ.

Embeddings are cached in memory by text, so each distinct text is encoded
once per scorer; no database or vector index is used. The encoder can be
injected (tests use a stub, so CI never downloads the model).

**Timeouts (IR-06).** Two different risks, handled differently:

- *Loading* the model can hang, because on a cold cache it fetches over the
  network. `DOWNLOAD_TIMEOUT_S` is passed to huggingface_hub, which applies it
  per request, so an unreachable hub fails instead of blocking startup forever.
- *Inference* cannot hang in the same way: it is bounded CPU work on text already
  truncated to the model's 256 word pieces. What it can do is take far longer
  than expected on a loaded machine. `ENCODE_BUDGET_S` bounds how long a caller
  waits: the encode runs on a worker thread and the caller gives up when the
  budget passes.

Two honest caveats on the second. It bounds the **wait**, not the work: a thread
that overran is left to finish and its result is discarded, so the memory is held
until it does. And the encode call must be left exactly as it was — passing the
whole list to `model.encode` in one go. Splitting it into batches here would be
the obvious way to check a deadline more often, but sentence-transformers sorts
by length internally to minimise padding, so encoding in two calls instead of one
changes the embeddings by about 1e-7. That is enough to perturb a near-tie and to
break reproducibility against the recorded runs. Measured, not assumed; see
`tests/test_semantic_scorer.py`.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

import numpy as np

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, MatchScore
from kaziforce_api.matching.base import Scorer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"  # Hugging Face commit, pinned for reproducibility
BATCH_SIZE = 32
DOWNLOAD_TIMEOUT_S = 30     # per network request while fetching the model
ENCODE_BUDGET_S = 120       # one embed() call; startup encodes 280 postings in about 25 s


class EncodeTimeout(RuntimeError):
    """The caller waited ENCODE_BUDGET_S for an embedding and gave up."""

Encoder = Callable[[list[str]], np.ndarray]


def worker_text(worker: EnrichedWorker) -> str:
    labels = worker.enrichment.labels()
    return worker.profile.biography + (" Skills: " + "; ".join(labels) + "." if labels else "")


def job_text(job: EnrichedJob) -> str:
    return job.profile.description


class SemanticScorer(Scorer):
    def __init__(self, model_name: str = MODEL_NAME, revision: str | None = MODEL_REVISION,
                 encoder: Encoder | None = None):
        self.model_name, self.revision = model_name, revision
        self._encoder = encoder
        self._injected = encoder is not None
        self._cache: dict[str, np.ndarray] = {}
        self.encoded = 0  # texts actually sent to the encoder (cache misses)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """L2-normalised embeddings, one row per text; each distinct text is encoded once."""
        missing = list(dict.fromkeys(t for t in texts if t not in self._cache))
        if missing:
            vectors = np.asarray(self._encode(missing), dtype=np.float32)
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.where(norms == 0, 1, norms)
            self._cache.update(zip(missing, vectors))
            self.encoded += len(missing)
        return np.stack([self._cache[t] for t in texts]) if texts else np.zeros((0, 0), dtype=np.float32)

    def score_many(self, worker: EnrichedWorker, jobs: Sequence[EnrichedJob]) -> np.ndarray:
        """Clipped cosine similarity of one worker against each job, in job order."""
        vectors = self.embed([worker_text(worker)] + [job_text(j) for j in jobs])
        return np.clip(vectors[1:] @ vectors[0], 0.0, 1.0)

    def score(self, worker: EnrichedWorker, job: EnrichedJob) -> float:
        return float(self.score_many(worker, [job])[0])

    def score_all(self, worker: EnrichedWorker, jobs: Sequence[EnrichedJob]) -> list[MatchScore]:
        scores = self.score_many(worker, jobs)
        return [MatchScore(worker.profile.worker_id, j.profile.posting_id, composite=float(s), semantic=float(s))
                for j, s in zip(jobs, scores)]

    def info(self) -> dict:
        return {"model": self.model_name, "revision": self.revision, "cached_texts": len(self._cache),
                "encoder": "injected" if self._injected else "sentence-transformers"}

    def _encode(self, texts: list[str]) -> np.ndarray:
        """One encode call, with a bound on how long the caller waits for it (IR-06).

        The list is passed whole, exactly as before this timeout existed: see the module
        docstring for why splitting it would change the numbers.
        """
        if self._encoder is None:
            self._encoder = self._load()
        if self._injected:
            return self._encoder(texts)  # a stub cannot hang, and tests should not spawn threads
        # Deliberately not a `with` block: ThreadPoolExecutor.__exit__ shuts down with
        # wait=True, which would block until the overrunning thread finished and make the
        # timeout do nothing at all.
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            return pool.submit(self._encoder, texts).result(timeout=ENCODE_BUDGET_S)
        except FutureTimeout:
            # The thread keeps running; we stop waiting for it. Python cannot interrupt CPU
            # work in another thread, and killing the process to do so would be worse.
            raise EncodeTimeout(f"embedding {len(texts)} texts took longer than "
                                f"{ENCODE_BUDGET_S}s") from None
        finally:
            pool.shutdown(wait=False)

    def _load(self) -> Encoder:
        from sentence_transformers import SentenceTransformer  # imported lazily: loading torch is slow

        # Bounds each network request while fetching the model; no effect once it is cached.
        os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", str(DOWNLOAD_TIMEOUT_S))
        model = SentenceTransformer(self.model_name, revision=self.revision, device="cpu")
        return lambda batch: model.encode(batch, batch_size=BATCH_SIZE, convert_to_numpy=True,
                                          normalize_embeddings=True, show_progress_bar=False)
