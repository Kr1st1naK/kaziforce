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
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from kaziforce_api.data.models import EnrichedJob, EnrichedWorker, MatchScore
from kaziforce_api.matching.base import Scorer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"  # Hugging Face commit, pinned for reproducibility
BATCH_SIZE = 32

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
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer  # imported lazily: loading torch is slow

            model = SentenceTransformer(self.model_name, revision=self.revision, device="cpu")
            self._encoder = lambda batch: model.encode(batch, batch_size=BATCH_SIZE, convert_to_numpy=True,
                                                       normalize_embeddings=True, show_progress_bar=False)
        return self._encoder(texts)
