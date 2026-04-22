from __future__ import annotations
import json
import uuid
from functools import lru_cache

import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.config import Settings as ChromaSettings

from backend.config import get_settings


class GoogleEmbeddingFunction(EmbeddingFunction):
    """ChromaDB embedding function backed by gemini-embedding-001."""

    def __call__(self, input: Documents) -> Embeddings:
        from backend.models.google import embed
        return embed(list(input), task_type="RETRIEVAL_DOCUMENT")


class GoogleQueryEmbeddingFunction(EmbeddingFunction):
    """Query-side embedding — uses RETRIEVAL_QUERY task type for better recall."""

    def __call__(self, input: Documents) -> Embeddings:
        from backend.models.google import embed
        return embed(list(input), task_type="RETRIEVAL_QUERY")


@lru_cache(maxsize=1)
def _client() -> chromadb.ClientAPI:
    cfg = get_settings()
    return chromadb.PersistentClient(
        path=cfg.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


@lru_cache(maxsize=1)
def _collection() -> chromadb.Collection:
    return _client().get_or_create_collection(
        name="d0mmy",
        embedding_function=GoogleEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


def store(text: str, metadata: dict | None = None) -> str:
    doc_id = str(uuid.uuid4())
    _collection().add(
        documents=[text],
        metadatas=[metadata or {}],
        ids=[doc_id],
    )
    return doc_id


def fetch_context(query: str, n_results: int = 5) -> list[dict]:
    results = _collection().query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    output: list[dict] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({"text": doc, "metadata": meta, "distance": round(dist, 4)})
    return output


def fetch_context_json(query: str, n_results: int = 5) -> str:
    return json.dumps(fetch_context(query, n_results))
