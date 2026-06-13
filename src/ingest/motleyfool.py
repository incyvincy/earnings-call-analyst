"""Motley Fool earnings call transcript scraper.

Finds transcripts via DuckDuckGo search, then scrapes the free article.
No API key needed — all publicly accessible content.
"""
from __future__ import annotations

import re
import time
from urllib.parse import parse_qs, quote, urlparse

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


def _find_url(ticker: str, year: int, quarter: int) -> str | None:
    """Search DuckDuckGo for the Motley Fool transcript page."""
    query = f"site:fool.com/earnings {ticker} Q{quarter} {year} earnings call transcript"
    search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    pattern = re.compile(r"fool\.com/earnings/call-transcripts/\d{4}/\d{2}/\d{2}/")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # DuckDuckGo wraps result links — unwrap them
        if "uddg=" in href:
            parsed = parse_qs(urlparse(href).query)
            href = parsed.get("uddg", [""])[0]
        if pattern.search(href):
            if not href.startswith("http"):
                href = "https://www.fool.com" + href
            # Make sure it matches the right quarter and year
            slug = href.split("/")[-2] if href.endswith("/") else href.split("/")[-1]
            if f"q{quarter}" in slug and str(year) in slug:
                return href

    return None


def _parse_transcript(url: str) -> str | None:
    """Fetch and extract plain text from the article page."""
    time.sleep(1.5)  # polite crawl delay
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove nav, ads, headers, footers before extracting text
    for tag in soup.find_all(["nav", "header", "footer", "script", "style", "aside"]):
        tag.decompose()

    # Motley Fool article body
    body = (
        soup.find("div", {"class": re.compile(r"article-body|content-block|tailwind-article-body")})
        or soup.find("article")
        or soup.find("main")
    )
    if not body:
        return None

    paragraphs = [p.get_text(separator=" ", strip=True) for p in body.find_all("p")]
    text = "\n\n".join(p for p in paragraphs if p)
    return text if len(text) > 300 else None


class MotleyFoolSource:
    def fetch(self, ticker: str, year: int, quarter: int) -> RawTranscript | None:
        print(f"  Searching Motley Fool for {ticker} Q{quarter} {year}...")
        url = _find_url(ticker, year, quarter)
        if not url:
            print(f"  Not found via search — skipping.")
            return None
        print(f"  Scraping: {url}")
        text = _parse_transcript(url)
        if not text:
            print(f"  Could not parse article text.")
            return None
        return RawTranscript(
            ticker=ticker,
            year=year,
            quarter=quarter,
            date=None,
            content=text,
        )
