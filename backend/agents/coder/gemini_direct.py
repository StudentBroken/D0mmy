"""
Gemini 3.1 Pro direct path — escalation when complexity ≥ 8 or Gemma failed ×2.
Gets MORE context than Gemma path: full files for all relevant modules, not just top hits.
"""
from __future__ import annotations
import json
import logging

from backend.agents.scout import ScoutReport
from backend.memory.rom import get_prompt, get_schema
from backend.models.client import call_model

logger = logging.getLogger(__name__)


def _build_context(
    node: dict,
    scout: ScoutReport,
    retrieved_files: dict[str, str],
    prev_issues: list[str],
    escalation_reason: str,
) -> str:
    parts: list[str] = []

    parts.append(f"## Task\n{node.get('label', '')}")
    parts.append(f"## Escalation Reason\n{escalation_reason}")

    # Full module index summary for all relevant modules
    if scout.relevant_modules:
        parts.append("\n## Module Index (relevant modules)")
        for m in scout.relevant_modules:
            parts.append(f"\n### `{m['id']}` — {m.get('name', '')}")
            parts.append(f"> {m.get('tldr', '')}")
            if m.get("tree"):
                parts.append(f"```\n{m['tree']}\n```")

    # All retrieved files — Gemini gets the full set
    if retrieved_files:
        parts.append("\n## File Contents (full context)")
        for path, content in retrieved_files.items():
            parts.append(f"\n### `{path}`\n```\n{content}\n```")

    # ChromaDB hits
    if scout.chroma_hits:
        hits_text = "\n".join(
            f"- [{h.get('metadata', {}).get('source', 'unknown')}] {h.get('text', '')[:300]}"
            for h in scout.chroma_hits[:6]
        )
        parts.append(f"\n## Harvested Context\n{hits_text}")

    # Web research
    if scout.web_context:
        parts.append(f"\n## Research\n{scout.web_context}")

    # Previous failure context
    if prev_issues:
        issues_text = "\n".join(f"- {i}" for i in prev_issues)
        parts.append(f"\n## Previous Attempts Failed\n{issues_text}")

    parts.append(f"\n## Instructions\n{get_prompt('gemini_direct_coder')}")
    return "\n".join(parts)


async def generate(
    node: dict,
    scout: ScoutReport,
    retrieved_files: dict[str, str],
    escalation_reason: str = "complexity ≥ 8",
    prev_issues: list[str] | None = None,
) -> dict | None:
    """
    Returns {file_path, content, summary} or None on failure.
    Context is stripped to: task + relevant modules + file contents only.
    """
    context = _build_context(
        node, scout, retrieved_files, prev_issues or [], escalation_reason
    )
    messages = [{"role": "user", "content": context}]

    logger.info(
        "gemini_direct: escalated node=%r reason=%r context_chars=%d",
        node.get("label", ""),
        escalation_reason,
        len(context),
    )

    try:
        result = await call_model(
            "heavy", messages,
            schema=get_schema("code_diff"),
            agent="gemini_direct",
            goal=f"implement (direct): {node.get('label', '')}",
        )
        parsed = result.get("parsed") or {}
        if not parsed.get("file_path") or not parsed.get("content"):
            logger.warning("gemini_direct: empty output")
            return None
        return parsed
    except Exception as exc:
        logger.error("gemini_direct failed: %s", exc)
        return None
