"""Transcript ingestion.

Defines a small data model and a pluggable fetcher.

Sources:
- local   : reads from data/transcripts/{TICKER}_{YEAR}_Q{Q}.txt  (free, default)
- fmp     : Financial Modeling Prep API (transcripts require paid plan)
- edgar   : SEC EDGAR 8-K exhibits (free, see edgar.py)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


class LocalSource:
    """Read transcripts from  data/transcripts/{TICKER}_{YEAR}_Q{Q}.txt

    Drop any plain-text transcript file there with that naming convention and
    it will be picked up automatically. No API key needed.
    """

    BASE = Path("data/transcripts")

    def fetch(self, ticker: str, year: int, quarter: int) -> RawTranscript | None:
        path = self.BASE / f"{ticker.upper()}_{year}_Q{quarter}.txt"
        if not path.exists():
            return None
        return RawTranscript(
            ticker=ticker,
            year=year,
            quarter=quarter,
            date=None,
            content=path.read_text(encoding="utf-8"),
        )


class FMPSource:
    """Financial Modeling Prep earnings call transcript endpoint.

    Note: transcripts require a paid FMP plan (free tier returns 403).
    """

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
    if settings.transcript_source == "local":
        Path("data/transcripts").mkdir(parents=True, exist_ok=True)
        return LocalSource()
    if settings.transcript_source == "motleyfool":
        from src.ingest.motleyfool import MotleyFoolSource
        return MotleyFoolSource()
    if settings.transcript_source == "fmp":
        return FMPSource()
    raise ValueError(f"Unknown transcript source: {settings.transcript_source}")


def fetch_recent(ticker: str, n_quarters: int, latest_year: int, latest_q: int):
    """Yield the last n_quarters transcripts walking backwards from a point."""
    src = get_source()
    y, q = latest_year, latest_q
    for _ in range(n_quarters):
        try:
            t = src.fetch(ticker, y, q)
        except Exception as e:
            print(f"  Skipping {ticker} Q{q} {y}: {e}")
            t = None
        if t and t.content:
            yield t
        q -= 1
        if q == 0:
            q, y = 4, y - 1
