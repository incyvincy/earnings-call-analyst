"""Minimal tests for the pure-logic pieces (no network/model needed).

    pytest -q
"""
from __future__ import annotations

from src.ingest.transcripts import RawTranscript
from src.process.chunker import chunk_transcript
from src.process.metadata import classify_role, period_label


def test_chunking_tags_sections():
    content = (
        "John Doe, Chief Executive Officer: Revenue grew strongly this quarter.\n"
        "Operator: We will now begin the question-and-answer session.\n"
        "Jane Roe, Analyst: How are margins trending?\n"
    )
    t = RawTranscript("AAPL", 2024, 3, "2024-08-01", content)
    chunks = chunk_transcript(t, target=50, overlap=10)
    assert chunks, "should produce at least one chunk"
    assert any(c.section == "prepared" for c in chunks)
    assert any(c.section == "qa" for c in chunks)


def test_role_classification():
    assert classify_role("John, Chief Financial Officer") == "cfo"
    assert classify_role("Jane, Analyst at Big Bank") == "analyst"
    assert classify_role(None) == "unknown"


def test_period_label():
    assert period_label(2025, 2) == "Q2 2025"
