"""
Main orchestrator for module indexing.

index_workspace(root, force=False) — scan all files, skip unchanged by checksum
index_files(paths, root)           — lazy index of specific files only (used by Phase 3 pipeline)
"""
from __future__ import annotations
import logging
from pathlib import Path

from backend.agents.module_indexer.ast_graph import checksum_only, parse_file
from backend.agents.module_indexer.file_summarizer import summarize_files
from backend.agents.module_indexer.module_grouper import group_modules
from backend.agents.module_indexer.index_writer import load_index, write_index

logger = logging.getLogger(__name__)

_SUPPORTED   = {".py", ".ts", ".tsx", ".js", ".jsx", ".dart"}
_EXCLUDE_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", "out", ".venv",
    "dist", "build", "data", ".vscode-test",
})


# ── File discovery ─────────────────────────────────────────────────────────────

def _collect_files(workspace_root: Path) -> list[tuple[str, Path]]:
    pairs: list[tuple[str, Path]] = []
    for path in workspace_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in _SUPPORTED:
            continue
        pairs.append((str(path.relative_to(workspace_root)), path))
    return pairs


def _stale_only(
    all_files: list[tuple[str, Path]],
    cached: dict[str, dict],
) -> list[tuple[str, Path]]:
    stale: list[tuple[str, Path]] = []
    for rel, abs_path in all_files:
        chk = checksum_only(abs_path)
        if chk is None:
            continue
        entry = cached.get(rel)
        if not entry or entry.get("checksum") != chk:
            stale.append((rel, abs_path))
    return stale


# ── Public API ─────────────────────────────────────────────────────────────────

async def index_workspace(workspace_root: str, force: bool = False) -> dict:
    """
    Scan all supported files under workspace_root.
    Skip files whose checksum matches the cached entry (unless force=True).
    Re-runs module grouping every time (groupings may shift even without file changes).
    """
    root = Path(workspace_root)
    all_files = _collect_files(root)
    existing  = load_index()
    cached    = existing.get("files", {})

    to_index = all_files if force else _stale_only(all_files, cached)
    logger.info(
        "index_workspace: %d/%d files need indexing (force=%s)",
        len(to_index), len(all_files), force,
    )

    new_summaries: dict[str, dict] = {}
    if to_index:
        new_summaries = await summarize_files(to_index)

    # Merge: start from cached, apply new, prune deleted
    valid_paths = {rel for rel, _ in all_files}
    merged = {k: v for k, v in cached.items() if k in valid_paths}
    merged.update(new_summaries)

    modules = await group_modules(merged)
    write_index(merged, modules, workspace_root)

    return {
        "indexed":     len(new_summaries),
        "total_files": len(merged),
        "modules":     len(modules),
        "skipped":     len(all_files) - len(to_index),
    }


async def index_files(file_paths: list[str], workspace_root: str) -> dict:
    """
    Index a specific subset of files (lazy path used by Phase 3 after diff accepted).
    Does NOT re-group — just updates the per-file entries and rewrites.
    Full re-group happens on next index_workspace call.
    """
    root  = Path(workspace_root)
    pairs = [(p, root / p) for p in file_paths if (root / p).exists()]
    if not pairs:
        return {"indexed": 0}

    new_summaries = await summarize_files(pairs)
    existing      = load_index()
    merged        = {**existing.get("files", {}), **new_summaries}

    modules = await group_modules(merged)
    write_index(merged, modules, workspace_root)

    return {"indexed": len(new_summaries), "modules": len(modules)}
