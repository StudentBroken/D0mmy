"""
File content retriever — no AI, pure disk reads.
Given module IDs from ScoutReport, loads actual file content
for injection into Coder/Gemini context.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_INDEX_PATH   = Path(__file__).resolve().parents[3] / "data" / "module_index.json"
_MAX_CHARS    = 6000   # per file, hard cap
_MAX_TOTAL    = 20000  # total chars across all retrieved files


def _load_index() -> dict:
    if _INDEX_PATH.exists():
        try:
            return json.loads(_INDEX_PATH.read_text())
        except Exception:
            pass
    return {"files": {}, "modules": []}


def retrieve_for_modules(
    module_ids: list[str],
    workspace_root: str,
) -> dict[str, str]:
    """
    Returns {rel_path: file_content} for all files belonging to the given modules.
    Content is truncated to _MAX_CHARS per file, total capped at _MAX_TOTAL.
    """
    root  = Path(workspace_root)
    index = _load_index()
    mod_map = {m["id"]: m for m in index.get("modules", [])}

    file_paths: list[str] = []
    for mid in module_ids:
        mod = mod_map.get(mid)
        if not mod:
            continue
        for f in mod.get("files", []):
            p = f.get("path", "")
            if p and p not in file_paths:
                file_paths.append(p)

    result: dict[str, str] = {}
    total_chars = 0

    for rel in file_paths:
        if total_chars >= _MAX_TOTAL:
            break
        abs_path = root / rel
        if not abs_path.is_file():
            continue
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("retriever: cannot read %s: %s", rel, exc)
            continue

        if len(content) > _MAX_CHARS:
            content = content[:_MAX_CHARS] + f"\n... ({len(content) - _MAX_CHARS} chars truncated)"

        result[rel] = content
        total_chars += len(content)

    logger.debug("retriever: %d files, %d total chars", len(result), total_chars)
    return result


def retrieve_file(rel_path: str, workspace_root: str) -> str | None:
    """Read a single file. Returns None if unreadable."""
    abs_path = Path(workspace_root) / rel_path
    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        if len(content) > _MAX_CHARS:
            content = content[:_MAX_CHARS] + f"\n... ({len(content) - _MAX_CHARS} chars truncated)"
        return content
    except OSError:
        return None
