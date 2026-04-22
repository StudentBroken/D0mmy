"""
Coder Dispatcher — routes each sprint node through the tiered execution pyramid.

Decision tree per node:
  1. Score complexity (Gemma daemon, fast)
  2. score < 8  → Gemma coder (attempt 1)
                   fail      → Gemma coder (attempt 2, with issues)
                   fail ×2   → escalate to Gemini direct
     score ≥ 8  → Gemini direct immediately
  3. Critic review (Gemini heavy, always)
     not approved → one retry of same path with critic issues injected
  4. Return approved diff or None
"""
from __future__ import annotations
import logging
from pathlib import Path

from backend.agents.scout import ScoutReport
from backend.agents.coder import complexity_scorer, retriever, module_coder, gemini_direct, critic

logger = logging.getLogger(__name__)

_MAX_GEMMA_ATTEMPTS = 2
_MAX_CRITIC_RETRIES = 1


async def dispatch_node(
    node: dict,
    scout: ScoutReport,
    workspace_root: str,
    session_id: str,
) -> dict | None:
    """
    Returns approved {file_path, content, summary} or None if all paths fail.
    """
    label = node.get("label", node.get("id", "unknown"))

    # ── 1. Score complexity ────────────────────────────────────────────────────
    complexity, reason = await complexity_scorer.score(
        task_description=scout.query,
        node_label=label,
    )
    escalate_immediately = complexity_scorer.should_escalate(complexity)

    if escalate_immediately:
        logger.info("dispatch: node=%r complexity=%d → direct path", label, complexity)
    else:
        logger.info("dispatch: node=%r complexity=%d → Gemma path", label, complexity)

    # ── 2. Retrieve file contents ──────────────────────────────────────────────
    module_ids = [m["id"] for m in scout.relevant_modules]
    files      = retriever.retrieve_for_modules(module_ids, workspace_root)

    # ── 3. Generate diff ───────────────────────────────────────────────────────
    diff: dict | None = None
    escalation_reason = f"complexity {complexity}/10"
    prev_issues: list[str] = []

    if escalate_immediately:
        diff = await gemini_direct.generate(
            node, scout, files,
            escalation_reason=escalation_reason,
        )
    else:
        # Gemma path — up to _MAX_GEMMA_ATTEMPTS
        for attempt in range(1, _MAX_GEMMA_ATTEMPTS + 1):
            diff = await module_coder.generate(
                node, scout, files,
                attempt=attempt,
                prev_issues=prev_issues,
            )
            if diff:
                break
            logger.warning("dispatch: Gemma attempt %d failed for node=%r", attempt, label)

        # Escalate if Gemma exhausted
        if not diff:
            escalation_reason = f"Gemma failed {_MAX_GEMMA_ATTEMPTS}×"
            logger.info("dispatch: escalating node=%r — %s", label, escalation_reason)
            diff = await gemini_direct.generate(
                node, scout, files,
                escalation_reason=escalation_reason,
            )

    if not diff:
        logger.error("dispatch: all paths failed for node=%r", label)
        return None

    # ── 4. Critic review loop ──────────────────────────────────────────────────
    for retry in range(_MAX_CRITIC_RETRIES + 1):
        original = _read_original(diff.get("file_path", ""), workspace_root)
        review   = await critic.review(
            diff=diff,
            original_content=original,
            task_description=f"{label}: {scout.query}",
        )

        if review["approved"]:
            logger.info("dispatch: critic approved node=%r", label)
            return diff

        prev_issues = review["issues"]
        logger.warning(
            "dispatch: critic rejected node=%r issues=%s (retry %d/%d)",
            label, prev_issues, retry + 1, _MAX_CRITIC_RETRIES,
        )

        if retry >= _MAX_CRITIC_RETRIES:
            break

        # Retry generation with critic issues — always use Gemini for fix
        diff = await gemini_direct.generate(
            node, scout, files,
            escalation_reason=f"critic rejected: {'; '.join(prev_issues[:2])}",
            prev_issues=prev_issues,
        )
        if not diff:
            break

    logger.error("dispatch: critic rejected and retries exhausted for node=%r", label)
    return None


def _read_original(rel_path: str, workspace_root: str) -> str:
    if not rel_path:
        return ""
    abs_path = Path(workspace_root) / rel_path
    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        return content[:4000]
    except OSError:
        return ""
