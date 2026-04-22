import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.config import Settings as ChromaSettings

from backend.config import get_settings

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


_clients: dict[str, chromadb.ClientAPI] = {}
_collections: dict[str, chromadb.Collection] = {}


def _client() -> chromadb.ClientAPI:
    cfg = get_settings()
    path = cfg.chroma_persist_dir
    if path not in _clients:
        Path(path).mkdir(parents=True, exist_ok=True)
        _clients[path] = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _clients[path]


def _collection() -> chromadb.Collection:
    cfg = get_settings()
    path = cfg.chroma_persist_dir
    if path not in _collections:
        _collections[path] = _client().get_or_create_collection(
            name="d0mmy",
            embedding_function=GoogleEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collections[path]


def store(text: str, metadata: dict | None = None) -> str:
    doc_id = str(uuid.uuid4())
    _collection().add(
        documents=[text],
        metadatas=[metadata or {}],
        ids=[doc_id],
    )
    return doc_id


async def fetch_context(query: str, n_results: int = 5) -> list[dict]:
    from backend.ws_manager import manager
    call_id = uuid.uuid4().hex[:8]
    t_start = time.monotonic()

    await manager.broadcast(
        {
            "type": "api_call",
            "payload": {
                "call_id": call_id,
                "agent": "chromadb",
                "role": "hdd",
                "model": "ChromaDB (Vector Storage)",
                "goal": f"Retrieve context for: {query[:40]}…",
                "status": "start",
            },
            "session_id": "system",
            "timestamp": _now(),
        },
        client_type="dashboard",
    )

    try:
        results = _collection().query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        duration_ms = int((time.monotonic() - t_start) * 1000)

        output: list[dict] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({"text": doc, "metadata": meta, "distance": round(dist, 4)})

        await manager.broadcast(
            {
                "type": "api_call",
                "payload": {
                    "call_id": call_id,
                    "agent": "chromadb",
                    "role": "hdd",
                    "model": "ChromaDB (Vector Storage)",
                    "goal": f"Retrieved {len(output)} documents",
                    "status": "complete",
                    "duration_ms": duration_ms,
                },
                "session_id": "system",
                "timestamp": _now(),
            },
            client_type="dashboard",
        )
        return output
    except Exception as exc:
        duration_ms = int((time.monotonic() - t_start) * 1000)
        await manager.broadcast(
            {
                "type": "api_call",
                "payload": {
                    "call_id": call_id,
                    "agent": "chromadb",
                    "role": "hdd",
                    "model": "ChromaDB (Vector Storage)",
                    "status": "error",
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
                "session_id": "system",
                "timestamp": _now(),
            },
            client_type="dashboard",
        )
        raise


async def fetch_context_json(query: str, n_results: int = 5) -> str:
    import json
    return json.dumps(await fetch_context(query, n_results))
