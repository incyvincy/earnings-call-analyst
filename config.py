"""Central configuration, loaded from environment.

Swap embedding / LLM / data-source backends here without touching pipeline code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # --- data source ---
    transcript_source: str = os.getenv("TRANSCRIPT_SOURCE", "motleyfool")  # motleyfool | local | fmp | edgar
    fmp_api_key: str = os.getenv("FMP_API_KEY", "")
    api_ninjas_key: str = os.getenv("API_NINJAS_KEY", "")
    sec_user_agent: str = os.getenv("SEC_USER_AGENT", "")

    # --- embeddings (local only — Groq has no embedding API) ---
    # "sbert" = all-MiniLM-L6-v2, fast general-purpose retrieval (default)
    # "finbert" = finance-tuned, swap in for domain-embedding experiments
    embed_backend: str = os.getenv("EMBED_BACKEND", "sbert")
    finbert_model: str = "ProsusAI/finbert"  # used for sentiment, not retrieval

    # --- reranker ---
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- generation (Google Gemini — free tier, OpenAI-compatible) ---
    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # --- vector store (ChromaDB — file-based, no Docker needed) ---
    chroma_path: str = os.getenv("CHROMA_PATH", "./data/chroma")
    collection: str = "earnings_calls"

    # --- chunking / retrieval params ---
    chunk_target_tokens: int = 350
    chunk_overlap_tokens: int = 60
    retrieve_k: int = 20      # pull this many from vector search
    rerank_k: int = 6         # keep this many after reranking


settings = Settings()
