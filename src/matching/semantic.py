"""
Semantic similarity matching component.

Uses a pre-trained sentence-transformer model (default: all-MiniLM-L6-v2,
see SENTENCE_MODEL_NAME in .env) to embed worker biographies and job
descriptions, then compares them via cosine similarity.
"""

import os
from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    model_name = os.getenv("SENTENCE_MODEL_NAME", "all-MiniLM-L6-v2")
    return SentenceTransformer(model_name)


def score(worker_bio: str, job_description: str) -> float:
    """Compute cosine similarity between a worker bio and job description.

    TODO(Sprint 4): implement embedding + cosine similarity, cache embeddings
    """
    raise NotImplementedError
