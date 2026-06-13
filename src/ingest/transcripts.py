"""Transcript ingestion.

Defines a small data model and a pluggable fetcher. Transcripts with the analyst
Q&A section come from providers like Financial Modeling Prep or API Ninjas;
EDGAR 8-K exhibits (see edgar.py) are a free fallback for prepared remarks only.

Verify each provider's terms of service and response schema against their live
docs — the parsing below is defensive and may need adjusting to the exact shape.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import requests

from config import settings


@dataclass
class RawTranscript:
    ticker: str
    year: int
    quarter: int           # 1..4
    date: str | None       # ISO date if provided
    content: str           # full raw transcript text


class TranscriptSource(Protocol):
    def fetch(self, ticker: str, year: int, quarter: int) -> RawTranscript | None: ...


class FMPSource:
    """Financial Modeling Prep earnings call transcript endpoint."""

    BASE = "https://financialmodelingprep.com/api/v3/earning_call_transcript"

    def fetch(self, ticker: str, year: int, quarter: int) -> RawTranscript | None:
        params = {"year": year, "quarter": quarter, "apikey": settings.fmp_api_key}
        resp = requests.get(f"{self.BASE}/{ticker}", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        item = data[0]
        return RawTranscript(
            ticker=ticker,
            year=year,
            quarter=quarter,
            date=item.get("date"),
            content=item.get("content", ""),
        )


def get_source() -> TranscriptSource:
    if settings.transcript_source == "fmp":
        return FMPSource()
    # TODO: add APINinjasSource, and EdgarSource (import from edgar.py)
    raise ValueError(f"Unknown transcript source: {settings.transcript_source}")


def fetch_recent(ticker: str, n_quarters: int, latest_year: int, latest_q: int):
    """Yield the last n_quarters transcripts walking backwards from a point."""
    src = get_source()
    y, q = latest_year, latest_q
    for _ in range(n_quarters):
        t = src.fetch(ticker, y, q)
        if t and t.content:
            yield t
        q -= 1
        if q == 0:
            q, y = 4, y - 1
