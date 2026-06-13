"""Cross-company comparison: ask the same question against two tickers and return
both grounded answers for a side-by-side view in the UI.
"""
from __future__ import annotations

from src.rag.engine import Answer, ask


def compare(question: str, ticker_a: str, ticker_b: str) -> dict[str, Answer]:
    return {
        ticker_a: ask(question, where={"ticker": ticker_a}),
        ticker_b: ask(question, where={"ticker": ticker_b}),
    }
