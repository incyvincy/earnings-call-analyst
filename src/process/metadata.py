"""Metadata helpers: classify speaker roles and normalise period labels.

Knowing whether a speaker is the CEO, CFO, or an external analyst lets you ask
questions like "what did the CFO say about margins" with a metadata filter
instead of hoping the embedding picks it up.
"""
from __future__ import annotations

CFO_HINTS = ("chief financial officer", "cfo")
CEO_HINTS = ("chief executive officer", "ceo")
ANALYST_HINTS = ("analyst", "research", "securities", "capital", "bank")


def classify_role(speaker: str | None, context: str = "") -> str:
    if not speaker:
        return "unknown"
    blob = f"{speaker} {context}".lower()
    if any(h in blob for h in CFO_HINTS):
        return "cfo"
    if any(h in blob for h in CEO_HINTS):
        return "ceo"
    if any(h in blob for h in ANALYST_HINTS):
        return "analyst"
    return "management" if speaker else "unknown"


def period_label(year: int, quarter: int) -> str:
    return f"Q{quarter} {year}"
