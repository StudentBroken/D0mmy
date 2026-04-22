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

_GLOBAL_DATA = Path(__file__).resolve().parents[3] / "data"

# Backward-compat constants — point to global data dir (used when no target_repo set)
INDEX_JSON = _GLOBAL_DATA / "module_index.json"
INDEX_MD   = _GLOBAL_DATA / "module_index.md"


def _d0mmy_dir(workspace_root: str | None = None) -> Path:
    """Return the .d0mmy data directory for the given workspace.
    Falls back to the global data/ dir when no workspace or target_repo is set."""
    root = workspace_root
    if not root:
        try:
            from backend.config import get_settings
            root = get_settings().target_repo
        except Exception:
            pass
    if root:
        d = Path(root) / ".d0mmy"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return _GLOBAL_DATA


def get_index_json_path(workspace_root: str | None = None) -> Path:
    return _d0mmy_dir(workspace_root) / "module_index.json"


def get_index_md_path(workspace_root: str | None = None) -> Path:
    return _d0mmy_dir(workspace_root) / "module_index.md"


def load_index(workspace_root: str | None = None) -> dict:
    path = get_index_json_path(workspace_root)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception as exc:
            logger.warning("Corrupt module_index.json at %s: %s — starting fresh", path, exc)
    return {"version": 1, "files": {}, "modules": []}


def write_index(
    file_summaries: dict[str, dict],
    modules: list[dict],
    workspace_root: str,
) -> None:
    index = load_index(workspace_root)
    index["version"]        = 1
    index["last_indexed"]   = datetime.now(timezone.utc).isoformat()
    index["workspace_root"] = workspace_root
    index["files"].update(file_summaries)
    index["modules"]        = modules

    json_path = get_index_json_path(workspace_root)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(index, indent=2))
    _write_md(index, workspace_root)
    logger.info(
        "module_index written to %s: %d files, %d modules",
        json_path.parent, len(index["files"]), len(modules),
    )


def _write_md(index: dict, workspace_root: str | None = None) -> None:
    ts   = index.get("last_indexed", "unknown")
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

    get_index_md_path(workspace_root).write_text("\n".join(lines))


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
    get_index_json_path().write_text(json.dumps(index, indent=2))
