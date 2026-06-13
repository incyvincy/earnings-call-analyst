"""Motley Fool earnings call transcript scraper.

Finds the transcript URL by scanning weekdays in a date window using fast
HEAD requests (no delay on 404, slow down only on 429). Then fetches and
parses the free article. No API key needed.
"""
from __future__ import annotations

import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

from src.ingest.transcripts import RawTranscript

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BASE = "https://www.fool.com/earnings/call-transcripts"

TICKER_SLUG = {
    "AAPL":  "apple",
    "MSFT":  "microsoft",
    "NVDA":  "nvidia",
    "GOOGL": "alphabet",
    "GOOG":  "alphabet",
    "AMZN":  "amazon",
    "META":  "meta-platforms",
    "TSLA":  "tesla",
    "NFLX":  "netflix",
    "AMD":   "advanced-micro-devices",
    "INTC":  "intel",
    "CRM":   "salesforce",
    "ORCL":  "oracle",
    "QCOM":  "qualcomm",
}

# Each Q{n} label in the URL slug → typical calendar months when the call
# is published (covers different fiscal year conventions across companies).
_QUARTER_MONTHS = {
    1: [(0, 10), (0, 11), (0, 12), (1, 1), (1, 2), (1, 3), (1, 4)],
    2: [(1, 1), (1, 2), (1, 4), (1, 5), (1, 6), (1, 7)],
    3: [(1, 4), (1, 5), (1, 7), (1, 8), (1, 9), (1, 10)],
    4: [(1, 7), (1, 8), (1, 10), (1, 11), (1, 12)],
}
# (year_offset, month): year_offset 0 = year-1, 1 = year


def _scan_url(ticker: str, year: int, quarter: int) -> str | None:
    """Scan weekdays across expected months using fast HEAD requests."""
    slug = TICKER_SLUG.get(ticker.upper())
    if not slug:
        print(f"  No slug for {ticker} — add to TICKER_SLUG in motleyfool.py")
        return None

    article_slug = f"{slug}-{ticker.lower()}-q{quarter}-{year}-earnings-call-transcript"
    months = _QUARTER_MONTHS.get(quarter, [])

    for year_offset, month in months:
        scan_year = (year - 1) if year_offset == 0 else year
        # Scan every weekday in this month
        d = date(scan_year, month, 1)
        while d.month == month:
            if d.weekday() < 5:  # Mon–Fri only
                url = f"{BASE}/{d.year}/{d.month:02d}/{d.day:02d}/{article_slug}/"
                try:
                    r = requests.head(url, headers=HEADERS, timeout=6, allow_redirects=True)
                    if r.status_code == 200:
                        return url
                    if r.status_code == 429:
                        print("  Rate limited — waiting 20 s...")
                        time.sleep(20)
                except Exception:
                    pass
            d += timedelta(days=1)
    return None


def _parse_transcript(url: str) -> str | None:
    """Fetch and extract plain text from the article."""
    time.sleep(1.5)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Fetch failed: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup.find_all(["nav", "header", "footer", "script", "style", "aside"]):
        tag.decompose()

    body = soup.find("div", class_=re.compile(r"article-body"))
    if not body:
        body = soup.find("article") or soup.find("main")
    if not body:
        return None

    paragraphs = [p.get_text(separator=" ", strip=True) for p in body.find_all("p")]
    text = "\n\n".join(p for p in paragraphs if p)
    return text if len(text) > 300 else None


class MotleyFoolSource:
    def fetch(self, ticker: str, year: int, quarter: int) -> RawTranscript | None:
        print(f"  Scanning for {ticker} Q{quarter} {year}...")
        url = _scan_url(ticker, year, quarter)
        if not url:
            print(f"  Not found — skipping.")
            return None
        print(f"  Found: {url}")
        text = _parse_transcript(url)
        if not text:
            print(f"  Could not parse article.")
            return None
        return RawTranscript(
            ticker=ticker, year=year, quarter=quarter, date=None, content=text
        )
