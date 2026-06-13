"""Speaker- and section-aware chunking.

Naive fixed-size chunking destroys the structure that makes earnings calls
useful. We keep speaker turns intact and tag each chunk with its section
(prepared remarks vs Q&A) so retrieval can filter on it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.ingest.transcripts import RawTranscript

# Heuristics -- tune to your provider's formatting. Names may include a comma +
# title, e.g. "Tim Cook, Chief Executive Officer:".
SPEAKER_RE = re.compile(r"^([A-Z][A-Za-z.\-' ]+(?:,[A-Za-z.\-' ]+)?):\s")
QA_MARKERS = ("question-and-answer", "q&a", "questions and answers")
# Phrases that mention Q&A as an upcoming event, not as a section header
_QA_PROSE = ("following", "will be a", "there will", "during the q&a", "after our prepared")


def _strip_markdown(line: str) -> str:
    """Remove Markdown formatting so the chunker sees plain text."""
    line = re.sub(r"\*+", "", line)          # **bold** / *italic*
    line = re.sub(r"^#+\s*", "", line)       # ## Heading
    line = re.sub(r"^-{3,}$", "", line)      # --- horizontal rule
    line = re.sub(r"^\d+\.\s+", "", line)    # "5. Q&A Section" → "Q&A Section"
    return line.strip()


@dataclass
class Chunk:
    text: str
    ticker: str
    year: int
    quarter: int
    date: str | None
    speaker: str | None
    section: str          # "prepared" | "qa"
    seq: int              # ordering within the call


@dataclass
class _Turn:
    speaker: str | None
    text: str
    section: str


def _split_turns(content: str) -> list[_Turn]:
    """Split a transcript into turns, tagging section at line granularity.

    The Q&A boundary is detected on its own line (operator hand-off / header), so
    a single un-delimited blob still sections correctly.
    """
    turns: list[_Turn] = []
    speaker: str | None = None
    section = "prepared"
    buf: list[str] = []

    def flush():
        if buf:
            turns.append(_Turn(speaker, " ".join(buf).strip(), section))
            buf.clear()

    for raw in content.splitlines():
        line = _strip_markdown(raw)
        if not line:
            continue
        low = line.lower()
        if section == "prepared" and any(mk in low for mk in QA_MARKERS):
            # Don't switch on operator prose: "there will be a question-and-answer session"
            if not any(p in low for p in _QA_PROSE):
                flush()
                section = "qa"
                continue
        m = SPEAKER_RE.match(line)
        if m:
            flush()
            speaker = m.group(1).strip()
            line = line[m.end():].strip()
        if line:
            buf.append(line)
    flush()
    return turns


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough; swap for a real tokenizer if needed


def chunk_transcript(t: RawTranscript, target: int = 350, overlap: int = 60) -> list[Chunk]:
    chunks: list[Chunk] = []
    seq = 0
    for turn in _split_turns(t.content):
        words = turn.text.split()
        if not words:
            continue
        step = max(1, target - overlap)
        for i in range(0, len(words), step):
            piece = " ".join(words[i : i + target])
            if _approx_tokens(piece) < 4:
                continue
            chunks.append(
                Chunk(
                    text=piece,
                    ticker=t.ticker,
                    year=t.year,
                    quarter=t.quarter,
                    date=t.date,
                    speaker=turn.speaker,
                    section=turn.section,
                    seq=seq,
                )
            )
            seq += 1
    return chunks
