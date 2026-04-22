"""
Groups file summaries into logical modules using Gemma 4 Worker + import graph hint.
Falls back to one-module-per-file if the model call fails.
"""
from __future__ import annotations
import logging

from backend.memory.rom import get_prompt, get_schema
from backend.models.client import call_model

logger = logging.getLogger(__name__)

_STDLIB_PREFIXES = frozenset({
    "os", "sys", "re", "json", "typing", "pathlib", "datetime", "asyncio",
    "logging", "collections", "functools", "itertools", "dataclasses",
    "contextlib", "hashlib", "uuid", "time", "math", "copy", "io",
    "subprocess", "threading", "multiprocessing",
})


def _is_internal(imp: str, all_paths: set[str]) -> bool:
    """True if the import string looks like an internal project module."""
    parts = imp.replace("/", ".").split(".")
    return any(p in imp for p in all_paths) or imp.startswith(("backend.", "dashboard.", "./", "../"))


def _build_grouper_input(file_summaries: dict[str, dict]) -> str:
    all_paths = set(file_summaries.keys())
    lines: list[str] = ["## Files and TLDRs\n"]

    for path in sorted(file_summaries):
        data = file_summaries[path]
        lines.append(f"- `{path}`: {data.get('tldr', '(no summary)')}")

    lines.append("\n## Import relationships (internal only)\n")
    for path in sorted(file_summaries):
        data = file_summaries[path]
        internal = [
            i for i in data.get("imports", [])
            if i.split(".")[0] not in _STDLIB_PREFIXES
            and not i.startswith(("react", "vite", "@types", "node_modules"))
        ]
        if internal:
            lines.append(f"- `{path}` → {', '.join(internal[:8])}")

    return "\n".join(lines)


async def group_modules(file_summaries: dict[str, dict]) -> list[dict]:
    if not file_summaries:
        return []

    prompt_input = _build_grouper_input(file_summaries)
    messages = [
        {
            "role": "user",
            "content": f"{prompt_input}\n\n{get_prompt('module_grouper')}",
        }
    ]

    try:
        result = await call_model(
            "worker", messages,
            schema=get_schema("module_group"),
            agent="module_grouper",
            goal="group files into logical modules",
        )
        parsed = result.get("parsed") or {}
        modules = parsed.get("modules", [])
        if modules:
            return _fill_missing_files(modules, file_summaries)
    except Exception as exc:
        logger.warning("module_grouper failed: %s — using fallback", exc)

    return _fallback_groups(file_summaries)


def _fill_missing_files(modules: list[dict], file_summaries: dict[str, dict]) -> list[dict]:
    """Ensure every file in file_summaries appears in at least one module."""
    covered: set[str] = set()
    for mod in modules:
        for f in mod.get("files", []):
            covered.add(f.get("path", ""))

    uncovered = set(file_summaries.keys()) - covered
    for path in sorted(uncovered):
        data = file_summaries[path]
        mod_id = path.replace("/", "-").replace(".", "-")
        modules.append({
            "id":    mod_id,
            "name":  path,
            "tldr":  data.get("tldr", ""),
            "files": [{"path": path}],
            "deps":  data.get("imports", [])[:5],
        })
    return modules


def _fallback_groups(file_summaries: dict[str, dict]) -> list[dict]:
    modules = []
    for path, data in sorted(file_summaries.items()):
        mod_id = path.replace("/", "-").replace(".", "-")
        modules.append({
            "id":    mod_id,
            "name":  path,
            "tldr":  data.get("tldr", ""),
            "files": [{"path": path}],
            "deps":  data.get("imports", [])[:5],
        })
    return modules
