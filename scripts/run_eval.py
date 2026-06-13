"""Run the benchmark and print metrics.

    python scripts/run_eval.py
"""
from __future__ import annotations

from src.eval.benchmark import load
from src.eval.metrics import retrieval_hit_at_k


def main() -> None:
    items = load()
    if not items:
        print("No benchmark found at data/benchmark.jsonl — build one first.")
        return
    hit = retrieval_hit_at_k(items)
    print(f"Benchmark size: {len(items)}")
    print(f"Retrieval hit@{__import__('config').settings.rerank_k}: {hit}")
    # TODO: wire in an LLM judge and report faithfulness + answer relevance.


if __name__ == "__main__":
    main()
