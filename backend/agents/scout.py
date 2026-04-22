"""
Phase 3.1 — Scout Handoff.
Runs two parallel workers on sprint approval:
  RepoSearcher: ChromaDB semantic search + module index keyword match
  WebSearcher:  Gemini heavy for patterns/docs from training knowledge
Returns ScoutReport consumed by the Coder dispatcher.
"""
from __future__ import annotations
import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from backend.memory.hdd import fetch_context
from backend.models.client import call_model

logger = logging.getLogger(__name__)

_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "module_index.json"
_CHROMA_N   = 8
_MODULE_TOP = 5   # max modules returned by relevance filter


@dataclass
class ScoutReport:
    sprint:           dict
    nodes:            list[dict]
    relevant_modules: list[dict]   # from module_index, sorted by relevance
    chroma_hits:      list[dict]   # from ChromaDB
    web_context:      str          = ""
    query:            str          = ""


# ── Module index relevance ─────────────────────────────────────────────────────

def _load_module_index() -> dict:
    if _INDEX_PATH.exists():
        try:
            return json.loads(_INDEX_PATH.read_text())
        except Exception:
            pass
    return {"modules": []}


def _score_module(module: dict, keywords: list[str]) -> int:
    haystack = (
        module.get("tldr", "") + " " +
        module.get("name", "") + " " +
        module.get("id", "") + " " +
        module.get("tree", "")
    ).lower()
    return sum(1 for kw in keywords if kw.lower() in haystack)


def _relevant_modules(keywords: list[str], top_n: int = _MODULE_TOP) -> list[dict]:
    index = _load_module_index()
    modules = index.get("modules", [])
    scored = [(m, _score_module(m, keywords)) for m in modules]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [m for m, score in scored if score > 0][:top_n]


# ── Repo Searcher ──────────────────────────────────────────────────────────────

async def _repo_search(query: str, keywords: list[str]) -> tuple[list[dict], list[dict]]:
    """Returns (chroma_hits, relevant_modules) — pure data retrieval, no AI."""
    try:
        hits = fetch_context(query, n_results=_CHROMA_N)
    except Exception as exc:
        logger.warning("ChromaDB query failed: %s", exc)
        hits = []

    modules = _relevant_modules(keywords)
    return hits, modules


# ── Web Searcher ───────────────────────────────────────────────────────────────

async def _web_search(task: str, sprint_title: str) -> str:
    """Gemini heavy — knowledge about patterns and approaches for this task."""
    messages = [
        {
            "role": "user",
            "content": (
                f"Sprint task: {sprint_title}\n\n"
                f"Implementation target: {task}\n\n"
                "Briefly describe: best implementation patterns, common pitfalls, "
                "and relevant library APIs for this task. Be terse and technical. "
                "Max 300 words."
            ),
        }
    ]
    try:
        result = await call_model(
            "heavy", messages,
            agent="web_searcher",
            goal=f"research patterns for: {sprint_title}",
        )
        return result.get("content", "")
    except Exception as exc:
        logger.warning("web_searcher failed: %s", exc)
        return ""


# ── Public API ─────────────────────────────────────────────────────────────────

async def run(sprint: dict, blueprint: dict) -> ScoutReport:
    node_map    = {n["id"]: n for n in blueprint.get("nodes", [])}
    sprint_nodes = [
        node_map[nid]
        for nid in sprint.get("node_ids", [])
        if nid in node_map and node_map[nid].get("type") != "hard_stop"
    ]

    # Build search query from sprint title + node labels
    labels   = [n.get("label", "") for n in sprint_nodes]
    query    = sprint.get("title", "") + " " + " ".join(labels)
    keywords = query.split()

    # Run repo and web search in parallel
    (chroma_hits, relevant_modules), web_ctx = await asyncio.gather(
        _repo_search(query, keywords),
        _web_search(" ".join(labels[:3]), sprint.get("title", "")),
    )

    logger.info(
        "Scout: sprint=%d nodes=%d modules=%d chroma_hits=%d",
        sprint.get("sprint_id", -1),
        len(sprint_nodes),
        len(relevant_modules),
        len(chroma_hits),
    )

    return ScoutReport(
        sprint=sprint,
        nodes=sprint_nodes,
        relevant_modules=relevant_modules,
        chroma_hits=chroma_hits,
        web_context=web_ctx,
        query=query,
    )
