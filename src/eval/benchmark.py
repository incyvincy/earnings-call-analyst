"""Evaluation benchmark.

A QA item pairs a question with the ground-truth quarter(s) it should retrieve
and a reference answer. Seed ~150-200 of these (generate candidates with an LLM,
then hand-verify — do not skip verification, auto-generated truth is noisy).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class QAItem:
    question: str
    ticker: str
    gold_periods: list[str]      # e.g. ["Q3 2024"] — for retrieval scoring
    reference_answer: str        # for answer-relevance / faithfulness scoring


def load(path: str = "data/benchmark.jsonl") -> list[QAItem]:
    p = Path(path)
    if not p.exists():
        return []
    items = []
    for line in p.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            items.append(QAItem(**d))
    return items


def save(items: list[QAItem], path: str = "data/benchmark.jsonl") -> None:
    Path(path).write_text(
        "\n".join(json.dumps(item.__dict__) for item in items)
    )
