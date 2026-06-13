"""Motley Fool earnings call transcript scraper.

Finds the transcript by scanning date ranges with lightweight HEAD requests,
then fetches and parses the free article. No API key needed.
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

# Motley Fool uses a company-name slug in the URL
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
    "IBM":   "ibm",
    "QCOM":  "qualcomm",
}

# For Q{n} {year}, scan dates centred on the typical reporting month
_QUARTER_CENTER_MONTH = {1: 2, 2: 5, 3: 8, 4: 11}


def _scan_for_url(ticker: str, year: int, quarter: int) -> str | None:
    """Try HEAD requests across a ±90-day window to find the transcript URL."""
    slug = TICKER_SLUG.get(ticker.upper())
    if not slug:
        print(f"  No URL slug mapping for {ticker} — add it to TICKER_SLUG in motleyfool.py")
        return None

    article_slug = f"{slug}-{ticker.lower()}-q{quarter}-{year}-earnings-call-transcript"
    center = date(year, _QUARTER_CENTER_MONTH[quarter], 1)
    start  = center - timedelta(days=90)
    end    = center + timedelta(days=90)

    current = start
    while current <= end:
        # Skip weekends — earnings calls never happen on Sat/Sun
        if current.weekday() < 5:
            url = f"{BASE}/{current.year}/{current.month:02d}/{current.day:02d}/{article_slug}/"
            try:
                r = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
                if r.status_code == 200:
                    return url
            except Exception:
                pass
            time.sleep(0.05)
        current += timedelta(days=1)
    return None


def _parse_transcript(url: str) -> str | None:
    """Fetch and extract plain text from the article page."""
    time.sleep(1.0)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception:
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
        print(f"  Scanning dates for {ticker} Q{quarter} {year}...")
        url = _scan_for_url(ticker, year, quarter)
        if not url:
            print(f"  Not found in date window — skipping.")
            return None
        print(f"  Found: {url}")
        text = _parse_transcript(url)
        if not text:
            print(f"  Could not parse article.")
            return None
        return RawTranscript(
            ticker=ticker,
            year=year,
            quarter=quarter,
            date=None,
            content=text,
        )
