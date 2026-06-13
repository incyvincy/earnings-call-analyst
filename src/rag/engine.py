"""RAG engine: retrieve -> rerank -> grounded generation.

Returns both the answer and the passages used, so the UI can show sources and
eval can score faithfulness.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from config import settings
from src.rag.prompts import SYSTEM, build_user_prompt
from src.rag.retriever import Passage, retrieve


@dataclass
class Answer:
    text: str
    passages: list[Passage]


@lru_cache(maxsize=1)
def _llm():
    from openai import OpenAI

    # Groq is OpenAI-compatible — only base_url changes
    return OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)


def ask(question: str, where: dict | None = None) -> Answer:
    passages = retrieve(question, where=where)
    if not passages:
        return Answer(text="No relevant passages found for that question.", passages=[])
    resp = _llm().chat.completions.create(
        model=settings.llm_model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_user_prompt(question, passages)},
        ],
    )
    return Answer(text=resp.choices[0].message.content, passages=passages)
