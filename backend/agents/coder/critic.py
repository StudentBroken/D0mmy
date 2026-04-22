"""
Gemini 3.1 Pro Critic — verifies every diff before it goes to VS Code.
Always runs regardless of which path (Gemma or Gemini direct) generated the diff.
BOM hardware check active only in hardware+software mode.
"""
from __future__ import annotations
import logging
from pathlib import Path

from backend.config import get_settings
from backend.memory.rom import get_prompt, get_schema
from backend.models.client import call_model

logger = logging.getLogger(__name__)


def _bom_context() -> str:
    if get_settings().project_mode != "hardware+software":
        return ""
    bom_path = Path(__file__).resolve().parents[3] / "data" / "bom.json"
    if not bom_path.exists():
        return ""
    try:
        return f"\n## Hardware BOM (reject any reference to hardware not listed)\n```json\n{bom_path.read_text()}\n```"
    except OSError:
        return ""


async def review(
    diff: dict,           # {file_path, content, summary}
    original_content: str,
    task_description: str,
) -> dict:
    """
    Returns {approved: bool, issues: [str], summary: str}.
    Raises on total model failure — caller handles retry.
    """
    bom_ctx = _bom_context()
    messages = [
        {
            "role": "user",
            "content": (
                f"## Task\n{task_description}\n"
                f"{bom_ctx}\n"
                f"## Original File (`{diff['file_path']}`)\n"
                f"```\n{original_content[:4000]}\n```\n"
                f"## Proposed New Content\n"
                f"```\n{diff.get('content', '')[:6000]}\n```\n"
                f"## Change Summary (from coder)\n{diff.get('summary', '')}\n\n"
                f"{get_prompt('code_critic')}"
            ),
        }
    ]

    result = await call_model(
        "heavy", messages,
        schema=get_schema("critic_review"),
        agent="code_critic",
        goal=f"review diff for: {diff.get('file_path', '')}",
    )
    parsed = result.get("parsed") or {}

    approved: bool      = bool(parsed.get("approved", False))
    issues:   list[str] = parsed.get("issues", [])
    summary:  str       = parsed.get("summary", "")

    logger.info(
        "critic: %s — approved=%s issues=%d",
        diff.get("file_path", ""),
        approved,
        len(issues),
    )
    return {"approved": approved, "issues": issues, "summary": summary}
