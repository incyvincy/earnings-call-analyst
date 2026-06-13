"""Retrieval = vector search (recall) then cross-encoder rerank (precision).

The reranker is cheap to add and is one of the clearest signals to a recruiter
that you understand RAG beyond the tutorial version.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from config import settings
from src.store.vectorstore import client, search


@dataclass
class Passage:
    text: str
    score: float
    meta: dict


@lru_cache(maxsize=1)
def _reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.reranker_model)


def retrieve(query: str, where: dict | None = None) -> list[Passage]:
    c = client()
    hits = search(c, query, k=settings.retrieve_k, where=where)
    candidates = [
        Passage(text=h.payload["text"], score=h.score, meta=h.payload) for h in hits
    ]
    if not candidates:
        return []
    pairs = [(query, p.text) for p in candidates]
    rerank_scores = _reranker().predict(pairs)
    for p, s in zip(candidates, rerank_scores):
        p.score = float(s)
    candidates.sort(key=lambda p: p.score, reverse=True)
    return candidates[: settings.rerank_k]
