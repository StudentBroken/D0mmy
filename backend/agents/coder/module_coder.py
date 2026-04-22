"""
Gemma 4 Worker coder — Gemma path (complexity < 8, attempt 1 or 2).
Gets retrieved file content + scout context → generates complete new file content.
"""
from __future__ import annotations
import logging

from backend.agents.scout import ScoutReport
from backend.memory.rom import get_prompt, get_schema
from backend.models.client import call_model

logger = logging.getLogger(__name__)


def _build_context(
    node: dict,
    scout: ScoutReport,
    retrieved_files: dict[str, str],
    attempt: int,
    prev_issues: list[str],
) -> str:
    parts: list[str] = []

    parts.append(f"## Task\n{node.get('label', '')}")
    if node.get("agent"):
        parts.append(f"Agent hint: {node['agent']}")

    if scout.web_context:
        parts.append(f"\n## Research Context\n{scout.web_context[:800]}")

    if scout.chroma_hits:
        hits_text = "\n".join(
            f"- {h.get('text', '')[:200]}" for h in scout.chroma_hits[:4]
        )
        parts.append(f"\n## Relevant Prior Context\n{hits_text}")

    if scout.relevant_modules:
        mod_lines = []
        for m in scout.relevant_modules[:4]:
            mod_lines.append(f"- `{m['id']}`: {m.get('tldr', '')}")
            if m.get("tree"):
                mod_lines.append(f"```\n{m['tree']}\n```")
        parts.append("\n## Relevant Modules\n" + "\n".join(mod_lines))

    if retrieved_files:
        parts.append("\n## File Contents")
        for path, content in retrieved_files.items():
            parts.append(f"\n### `{path}`\n```\n{content}\n```")

    if attempt > 1 and prev_issues:
        issues_text = "\n".join(f"- {i}" for i in prev_issues)
        parts.append(f"\n## Previous Attempt Failed — Fix These Issues\n{issues_text}")

    parts.append(f"\n## Instructions\n{get_prompt('module_coder')}")
    return "\n".join(parts)


async def generate(
    node: dict,
    scout: ScoutReport,
    retrieved_files: dict[str, str],
    attempt: int = 1,
    prev_issues: list[str] | None = None,
) -> dict | None:
    """
    Returns {file_path, content, summary} or None on failure.
    """
    context = _build_context(node, scout, retrieved_files, attempt, prev_issues or [])
    messages = [{"role": "user", "content": context}]

    try:
        result = await call_model(
            "worker", messages,
            schema=get_schema("code_diff"),
            agent="module_coder",
            goal=f"implement: {node.get('label', '')} (attempt {attempt})",
        )
        parsed = result.get("parsed") or {}
        if not parsed.get("file_path") or not parsed.get("content"):
            logger.warning("module_coder: empty output on attempt %d", attempt)
            return None
        return parsed
    except Exception as exc:
        logger.warning("module_coder failed (attempt %d): %s", attempt, exc)
        return None
