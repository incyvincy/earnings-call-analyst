"""End-to-end offline pipeline: fetch -> chunk -> embed -> store.

Usage:
    python scripts/build_index.py --tickers AAPL MSFT NVDA --quarters 8 \
        --latest-year 2025 --latest-q 2
"""
from __future__ import annotations

import argparse

from tqdm import tqdm

from config import settings
from src.ingest.transcripts import fetch_recent
from src.process.chunker import chunk_transcript
from src.store.vectorstore import client, ensure_collection, upsert_chunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", required=True)
    ap.add_argument("--quarters", type=int, default=8)
    ap.add_argument("--latest-year", type=int, required=True)
    ap.add_argument("--latest-q", type=int, required=True)
    args = ap.parse_args()

    c = client()
    ensure_collection(c)

    total = 0
    for ticker in args.tickers:
        for t in tqdm(
            fetch_recent(ticker, args.quarters, args.latest_year, args.latest_q),
            desc=ticker,
        ):
            chunks = chunk_transcript(
                t, settings.chunk_target_tokens, settings.chunk_overlap_tokens
            )
            total += upsert_chunks(c, chunks)

    print(f"Indexed {total} chunks into '{settings.collection}'.")


if __name__ == "__main__":
    main()
