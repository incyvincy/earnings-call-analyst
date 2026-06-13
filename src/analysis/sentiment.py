"""Temporal sentiment: run FinBERT-tone over a company's prepared remarks per
quarter and produce a drift series. This is the analytical layer that lifts the
project above a chatbot.

Optionally scope to a topic (e.g. "China", "margins") by filtering chunks whose
text mentions it before scoring.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from config import settings
from src.store.vectorstore import client, get_all


@lru_cache(maxsize=1)
def _finbert():
    from transformers import pipeline

    return pipeline("text-classification", model=settings.finbert_model, top_k=None)


def _score_to_signed(label_scores: list[dict]) -> float:
    """Map FinBERT-tone {positive, negative, neutral} to a single signed score."""
    d = {x["label"].lower(): x["score"] for x in label_scores}
    return d.get("positive", 0.0) - d.get("negative", 0.0)


def sentiment_by_quarter(ticker: str, topic: str | None = None) -> dict[str, float]:
    """Return {"Q1 2024": 0.42, ...} averaged sentiment per quarter."""
    c = client()
    hits = get_all(c, where={"ticker": ticker, "section": "prepared"})
    buckets: dict[str, list[float]] = defaultdict(list)
    clf = _finbert()
    for hit in hits:
        text = hit.payload["text"]
        if topic:
            t = topic.lower()
            if t not in text.lower() and t.rstrip("s") not in text.lower():
                continue
        period = f"Q{hit.payload['quarter']} {hit.payload['year']}"
        signed = _score_to_signed(clf(text[:512])[0])
        buckets[period].append(signed)
    return {p: round(sum(v) / len(v), 3) for p, v in buckets.items() if v}
