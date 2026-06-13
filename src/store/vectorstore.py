"""ChromaDB wrapper: create collection, upsert chunks with metadata payloads,
and run filtered similarity search. Persists to disk — no Docker required.

The metadata payload (ticker, year, quarter, speaker, role, section) powers
questions like "the CFO, in Q3, about margins" via filters + vector search.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from functools import lru_cache

from config import settings
from src.embed.embedder import embed
from src.process.chunker import Chunk
from src.process.metadata import classify_role


@dataclass
class Hit:
    payload: dict
    score: float


def _chroma_where(where: dict) -> dict:
    """Convert a flat {key: val} dict to ChromaDB filter syntax."""
    if len(where) == 1:
        key, val = next(iter(where.items()))
        return {key: {"$eq": val}}
    return {"$and": [{k: {"$eq": v}} for k, v in where.items()]}


@lru_cache(maxsize=1)
def client():
    import chromadb

    return chromadb.PersistentClient(path=settings.chroma_path)


def ensure_collection(c):
    return c.get_or_create_collection(
        name=settings.collection,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(c, chunks: list[Chunk]) -> int:
    if not chunks:
        return 0
    col = ensure_collection(c)
    vectors = embed([ch.text for ch in chunks])
    ids, embeddings, documents, metadatas = [], [], [], []
    for ch, vec in zip(chunks, vectors):
        payload = asdict(ch)
        payload["role"] = classify_role(ch.speaker)
        ids.append(str(uuid.uuid4()))
        embeddings.append(vec)
        documents.append(ch.text)
        # ChromaDB metadata values must be str / int / float / bool
        metadatas.append({k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool))})
    col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return len(ids)


def search(c, query: str, k: int, where: dict | None = None) -> list[Hit]:
    col = ensure_collection(c)
    qvec = embed([query])[0]
    kwargs: dict = {
        "query_embeddings": [qvec],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = _chroma_where(where)
    result = col.query(**kwargs)
    hits = []
    for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        payload = dict(meta)
        payload["text"] = doc
        # ChromaDB cosine distance = 1 - similarity; convert back to similarity score
        hits.append(Hit(payload=payload, score=1.0 - dist))
    return hits


def get_all(c, where: dict | None = None) -> list[Hit]:
    """Fetch all matching documents — used by sentiment analysis instead of Qdrant scroll."""
    col = ensure_collection(c)
    kwargs: dict = {"include": ["documents", "metadatas"]}
    if where:
        kwargs["where"] = _chroma_where(where)
    result = col.get(**kwargs)
    hits = []
    for doc, meta in zip(result["documents"], result["metadatas"]):
        payload = dict(meta)
        payload["text"] = doc
        hits.append(Hit(payload=payload, score=1.0))
    return hits
