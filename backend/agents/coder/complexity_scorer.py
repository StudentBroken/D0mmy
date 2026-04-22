"""Gemma daemon scores task complexity 0–10 before dispatch routing."""
from __future__ import annotations
import logging

from backend.memory.rom import get_prompt, get_schema
from backend.models.client import call_model

logger = logging.getLogger(__name__)

_ESCALATE_THRESHOLD = 8


async def score(task_description: str, node_label: str) -> tuple[int, str]:
    """
    Returns (score: int, reason: str).
    score ≥ _ESCALATE_THRESHOLD → caller should use Gemini direct path.
    """
    messages = [
        {
            "role": "user",
            "content": (
                f"Node: {node_label}\n"
                f"Task: {task_description}\n\n"
                f"{get_prompt('complexity_scorer')}"
            ),
        }
    ]
    try:
        result = await call_model(
            "daemon", messages,
            schema=get_schema("complexity_score"),
            agent="complexity_scorer",
            goal=f"score complexity: {node_label}",
        )
        parsed = result.get("parsed") or {}
        raw_score = parsed.get("score", 5)
        # Clamp to valid range
        s = max(0, min(10, int(raw_score)))
        reason = parsed.get("reason", "")
        logger.info("complexity_score: %d/10 — %s", s, reason)
        return s, reason
    except Exception as exc:
        logger.warning("complexity_scorer failed: %s — defaulting to 5", exc)
        return 5, "scorer unavailable"


def should_escalate(score_val: int) -> bool:
    return score_val >= _ESCALATE_THRESHOLD
