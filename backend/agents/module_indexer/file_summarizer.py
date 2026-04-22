"""
Per-file summarizer. Calls Gemma 4 Worker to produce tldr + markdown symbol tree.
Runs with bounded concurrency (default 5 parallel) to avoid rate-limit spikes.
"""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path

from backend.agents.module_indexer.ast_graph import FileGraph, parse_file
from backend.memory.rom import get_prompt, get_schema
from backend.models.client import call_model

logger = logging.getLogger(__name__)

_MAX_FILE_CHARS = 6000
_STDLIBS = frozenset({
    "os", "sys", "re", "json", "typing", "pathlib", "datetime", "asyncio",
    "logging", "collections", "functools", "itertools", "dataclasses",
    "contextlib", "hashlib", "uuid", "time", "math", "copy", "io",
})


def _symbol_hint(graph: FileGraph) -> str:
    lines = []
    for s in graph.symbols[:60]:
        loc = f"{s.kind} {s.name}:{s.line}"
        if s.parent:
            loc += f" (in {s.parent})"
        lines.append(f"  {loc}")
    return "\n".join(lines) or "  (no symbols detected)"


async def summarize_file(rel_path: str, abs_path: Path) -> dict | None:
    graph = parse_file(rel_path, abs_path)
    if graph is None:
        return None

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    body = content[:_MAX_FILE_CHARS]
    if len(content) > _MAX_FILE_CHARS:
        body += f"\n... ({len(content) - _MAX_FILE_CHARS} chars truncated)"

    messages = [
        {
            "role": "user",
            "content": (
                f"File: `{rel_path}`\n\n"
                f"Detected symbols:\n{_symbol_hint(graph)}\n\n"
                f"Content:\n```\n{body}\n```\n\n"
                f"{get_prompt('file_summarizer')}"
            ),
        }
    ]

    try:
        result = await call_model(
            "worker", messages,
            schema=get_schema("file_summary"),
            agent="file_summarizer",
            goal=f"summarize {rel_path}",
        )
    except Exception as exc:
        logger.warning("file_summarizer failed for %s: %s", rel_path, exc)
        return None

    parsed = result.get("parsed") or {}
    if not parsed.get("tldr"):
        return None

    return {
        "path":     rel_path,
        "checksum": graph.checksum,
        "tldr":     parsed.get("tldr", ""),
        "tree":     parsed.get("tree", ""),
        "symbols":  [
            {"name": s.name, "line": s.line, "kind": s.kind, "parent": s.parent}
            for s in graph.symbols
        ],
        "imports":  [i for i in graph.imports if i.split(".")[0] not in _STDLIBS],
    }


async def summarize_files(
    file_pairs: list[tuple[str, Path]],
    concurrency: int = 5,
) -> dict[str, dict]:
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(rel: str, abs_: Path) -> tuple[str, dict | None]:
        async with sem:
            return rel, await summarize_file(rel, abs_)

    results = await asyncio.gather(*[_bounded(r, a) for r, a in file_pairs])
    return {rel: data for rel, data in results if data is not None}
