"""
Reads and writes data/module_index.json + auto-generates data/module_index.md.
module_index.json = canonical machine-readable store.
module_index.md   = human-readable markdown tree view (edit then POST /index/sync to push back).
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT       = Path(__file__).resolve().parents[3]   # project root
INDEX_JSON  = _ROOT / "data" / "module_index.json"
INDEX_MD    = _ROOT / "data" / "module_index.md"


def load_index() -> dict:
    if INDEX_JSON.exists():
        try:
            return json.loads(INDEX_JSON.read_text())
        except Exception as exc:
            logger.warning("Corrupt module_index.json: %s — starting fresh", exc)
    return {"version": 1, "files": {}, "modules": []}


def write_index(
    file_summaries: dict[str, dict],
    modules: list[dict],
    workspace_root: str,
) -> None:
    index = load_index()
    index["version"]        = 1
    index["last_indexed"]   = datetime.now(timezone.utc).isoformat()
    index["workspace_root"] = workspace_root
    index["files"].update(file_summaries)
    index["modules"]        = modules

    INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    INDEX_JSON.write_text(json.dumps(index, indent=2))
    _write_md(index)
    logger.info(
        "module_index written: %d files, %d modules",
        len(index["files"]), len(modules),
    )


def _write_md(index: dict) -> None:
    ts  = index.get("last_indexed", "unknown")
    root = index.get("workspace_root", "")
    lines = [
        "# Module Index",
        f"> Last indexed: {ts}  |  Workspace: `{root}`",
        "",
        "---",
        "",
    ]

    for mod in index.get("modules", []):
        lines.append(f"## `{mod['id']}` — {mod['name']}")
        lines.append(f"> {mod['tldr']}")
        lines.append("")

        files_str = "  ".join(f"`{f['path']}`" for f in mod.get("files", []))
        lines.append(f"**Files:** {files_str}")

        if mod.get("deps"):
            lines.append(f"**Deps:** {', '.join(str(d) for d in mod['deps'][:8])}")

        # Per-file symbol trees
        for f in mod.get("files", []):
            fdata = index["files"].get(f["path"]) or {}
            tree = fdata.get("tree", "")
            if tree:
                lines.append("")
                lines.append("```")
                lines.append(tree)
                lines.append("```")

        lines.append("")
        lines.append("---")
        lines.append("")

    INDEX_MD.write_text("\n".join(lines))


def get_module_by_id(module_id: str) -> dict | None:
    index = load_index()
    for mod in index.get("modules", []):
        if mod.get("id") == module_id:
            return mod
    return None


def get_file_entry(rel_path: str) -> dict | None:
    index = load_index()
    return index.get("files", {}).get(rel_path)


def invalidate_file(rel_path: str) -> None:
    """Remove a file entry so it gets re-indexed on next run."""
    index = load_index()
    index.get("files", {}).pop(rel_path, None)
    INDEX_JSON.write_text(json.dumps(index, indent=2))
