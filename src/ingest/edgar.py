"""SEC EDGAR fallback: pull 8-K filings whose exhibits often contain the
prepared-remarks portion of an earnings release. No analyst Q&A, but free.

EDGAR requires a descriptive User-Agent header (set SEC_USER_AGENT in .env).
This is a thin starter — fill in the exhibit parsing for your needs.
"""
from __future__ import annotations

import requests

from config import settings

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def _headers() -> dict:
    if not settings.sec_user_agent:
        raise RuntimeError("Set SEC_USER_AGENT in .env (EDGAR requires it).")
    return {"User-Agent": settings.sec_user_agent}


def recent_8k_accessions(cik: int, limit: int = 12) -> list[str]:
    """Return recent 8-K accession numbers for a company CIK."""
    resp = requests.get(SUBMISSIONS.format(cik=cik), headers=_headers(), timeout=30)
    resp.raise_for_status()
    recent = resp.json()["filings"]["recent"]
    out = []
    for form, acc in zip(recent["form"], recent["accessionNumber"]):
        if form == "8-K":
            out.append(acc)
        if len(out) >= limit:
            break
    return out


# TODO: given an accession, fetch the filing index, locate the press-release
# exhibit (EX-99.1), download it, and strip HTML to plain text. Return a
# RawTranscript-compatible object so the rest of the pipeline is unchanged.
