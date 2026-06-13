"""Motley Fool earnings call transcript scraper.

Strategy: fetch the company's Motley Fool quote page (1 request per ticker)
to discover transcript URLs, then scrape the matching article.
No API key needed — all free public content.
"""
from __future__ import annotations

import re
import time

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

# Motley Fool company quote page — lists recent earnings transcripts
QUOTE_URL = "https://www.fool.com/quote/nasdaq/{ticker}/"

# Fallback: directly guess the article URL if the quote page doesn't work
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

# Exchange suffix per ticker (needed for quote page URL)
TICKER_EXCHANGE = {
    "AAPL": "nasdaq", "MSFT": "nasdaq", "NVDA": "nasdaq",
    "GOOGL": "nasdaq", "GOOG": "nasdaq", "AMZN": "nasdaq",
    "META": "nasdaq", "TSLA": "nasdaq", "NFLX": "nasdaq",
    "AMD": "nasdaq", "INTC": "nasdaq", "CRM": "nyse",
    "ORCL": "nyse", "QCOM": "nasdaq",
}


def _get(url: str, stream: bool = False) -> requests.Response | None:
    """GET with a polite delay and error handling."""
    time.sleep(2.0)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, stream=stream)
        if r.status_code == 429:
            print("  Rate limited — waiting 30 s...")
            time.sleep(30)
            r = requests.get(url, headers=HEADERS, timeout=20, stream=stream)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def _find_url_from_quote_page(ticker: str, year: int, quarter: int) -> str | None:
    """Fetch the company quote page and extract the matching transcript link."""
    exchange = TICKER_EXCHANGE.get(ticker.upper(), "nasdaq")
    url = f"https://www.fool.com/quote/{exchange}/{ticker.lower()}/"
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    pattern = re.compile(
        rf"/earnings/call-transcripts/\d{{4}}/\d{{2}}/\d{{2}}/.*-{ticker.lower()}-q{quarter}-{year}",
        re.IGNORECASE,
    )
    for a in soup.find_all("a", href=True):
        if pattern.search(a["href"]):
            href = a["href"]
            return href if href.startswith("http") else "https://www.fool.com" + href
    return None


def _find_url_direct_guess(ticker: str, year: int, quarter: int) -> str | None:
    """Try to guess the URL by checking a narrow window of likely months.

    Earnings calls typically happen 3–6 weeks after the quarter ends.
    We try just 3–4 candidate months with a 2-second delay between each.
    """
    slug = TICKER_SLUG.get(ticker.upper())
    if not slug:
        return None

    article_slug = f"{slug}-{ticker.lower()}-q{quarter}-{year}-earnings-call-transcript"

    # Candidate months: call for Q{n} fiscal year {year} might be published in
    # several different calendar months depending on fiscal year start.
    # Try a broad set: all 12 months of `year` + Oct-Dec of year-1.
    from datetime import date, timedelta

    candidates: list[date] = []
    for m in range(1, 13):
        # 3rd Wednesday of each month — a common earnings release day
        d = date(year, m, 1)
        weekday_offset = (2 - d.weekday()) % 7  # next Wednesday
        candidates.append(d + timedelta(days=weekday_offset + 14))  # 3rd Wed
    # Also try Oct-Dec of prior year
    for m in (10, 11, 12):
        d = date(year - 1, m, 1)
        weekday_offset = (2 - d.weekday()) % 7
        candidates.append(d + timedelta(days=weekday_offset + 14))

    for candidate in candidates:
        url = (
            f"{BASE}/{candidate.year}/{candidate.month:02d}/"
            f"{candidate.day:02d}/{article_slug}/"
        )
        resp = _get(url, stream=True)
        if resp and resp.status_code == 200:
            resp.close()
            return url
    return None


def _parse_transcript(url: str) -> str | None:
    """Fetch and extract plain text from the article page."""
    resp = _get(url)
    if not resp:
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
        print(f"  Finding transcript for {ticker} Q{quarter} {year}...")

        # Try 1: parse the company quote page for transcript links
        url = _find_url_from_quote_page(ticker, year, quarter)

        # Try 2: guess candidate dates
        if not url:
            print(f"  Quote page didn't have link — trying date guesses...")
            url = _find_url_direct_guess(ticker, year, quarter)

        if not url:
            print(f"  Could not find URL — skipping.")
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
