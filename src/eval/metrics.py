"""Eval metrics.

- retrieval hit@k: did we retrieve a passage from a gold period?
- faithfulness: is each answer claim supported by the retrieved passages?
  (LLM-as-judge; swap in RAGAS if you want a standard library.)
- answer relevance: does the answer address the question?

Report the numbers. "87% hit@6, 0.91 faithfulness on a 180-question benchmark"
is the line that closes the interview.
"""
from __future__ import annotations

from src.rag.engine import ask
from src.eval.benchmark import QAItem


def retrieval_hit_at_k(items: list[QAItem]) -> float:
    if not items:
        return 0.0
    hits = 0
    for it in items:
        ans = ask(it.question, where={"ticker": it.ticker})
        periods = {f"Q{p.meta['quarter']} {p.meta['year']}" for p in ans.passages}
        if periods & set(it.gold_periods):
            hits += 1
    return round(hits / len(items), 3)


def faithfulness(items: list[QAItem], judge) -> float:
    """`judge(answer_text, passages) -> float in [0,1]`. Plug in an LLM judge."""
    if not items:
        return 0.0
    scores = []
    for it in items:
        ans = ask(it.question, where={"ticker": it.ticker})
        scores.append(judge(ans.text, ans.passages))
    return round(sum(scores) / len(scores), 3)
