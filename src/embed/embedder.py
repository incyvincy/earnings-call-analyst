"""Local sentence embeddings — no API key required.

all-MiniLM-L6-v2 runs fine on CPU and gives solid retrieval quality.
Swap the model name here if you want a finance-tuned SBERT variant.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def embed(texts: list[str]) -> list[list[float]]:
    return _model().encode(texts, normalize_embeddings=True).tolist()


def embedding_dim() -> int:
    return 384
