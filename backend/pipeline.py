"""
Planning Pipeline — Phase 2 orchestrator.
Runs intent → clarify → route → idea builder (Map) → roadmap creator (Reduce) → broadcast.
Each step broadcasts status to all connected dashboard clients.
"""

from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone

from backend.ws_manager import manager

logger = logging.getLogger(__name__)

# Active pipelines keyed by session_id.
_active: dict[str, asyncio.Task] = {}

# Futures awaiting clarification answers: session_id → Future[list[dict]]
_pending_clarification: dict[str, asyncio.Future] = {}

# Futures awaiting improve feedback: session_id → Future[str]
_pending_improve: dict[str, asyncio.Future] = {}

CLARIFICATION_TIMEOUT_S = 300  # 5 minutes


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status(session_id: str, state: str, detail: str = "") -> dict:
    return {
        "type": "status_update",
        "payload": {"state": state, "detail": detail, "session_id": session_id},
        "session_id": session_id,
        "timestamp": _now(),
    }


async def _broadcast(session_id: str, state: str, detail: str = "") -> None:
    await manager.broadcast(_status(session_id, state, detail), client_type="dashboard")


async def _run_pipeline(session_id: str, intent_text: str, extra_context: str = "") -> None:
    from backend.agents.intent_router import classify
    from backend.agents.clarifier import generate_questions
    from backend.agents.idea_builder import run as build_ideas
    from backend.agents.roadmap_creator import run as create_roadmap

    try:
        # ── 1. Classify intent ────────────────────────────────────────────────
        await _broadcast(session_id, "routing", "Classifying intent…")
        classification = await classify(intent_text)
        intent_kind = classification["intent"]
        await _broadcast(session_id, "routing", f"Intent: {intent_kind} (confidence={classification['confidence']:.0%})")

        # ── 2. Clarification questions ────────────────────────────────────────
        await _broadcast(session_id, "clarifying", "Generating clarifying questions…")
        try:
            from backend.agents.module_indexer.index_writer import INDEX_MD
            _repo_map = ""
            if INDEX_MD.exists():
                _repo_map = INDEX_MD.read_text(encoding="utf-8", errors="replace")
                if len(_repo_map) > 12000:
                    _repo_map = _repo_map[:12000] + "\n... (truncated)"
            questions = await generate_questions(intent_text, repo_map=_repo_map)
        except Exception as exc:
            logger.warning("Clarifier failed (skipping): %s", exc)
            questions = []

        if questions:
            fut: asyncio.Future = asyncio.get_running_loop().create_future()
            _pending_clarification[session_id] = fut

            await manager.broadcast(
                {
                    "type": "clarification_needed",
                    "payload": {
                        "session_id": session_id,
                        "questions": questions,
                    },
                    "session_id": session_id,
                    "timestamp": _now(),
                },
                client_type="dashboard",
            )

            await _broadcast(session_id, "awaiting_clarification", f"Waiting for answers to {len(questions)} question(s)…")

            try:
                answers: list[dict] = await asyncio.wait_for(fut, timeout=CLARIFICATION_TIMEOUT_S)
                # Format answers as additional context block
                answers_text = "\n".join(
                    f"Q: {a.get('question', '')}\nA: {a.get('answer', '').strip()}"
                    for a in answers
                    if a.get("answer", "").strip()
                )
                if answers_text:
                    extra_context = answers_text
                await _broadcast(session_id, "building", "Answers received — proceeding with full context…")
            except asyncio.TimeoutError:
                await _broadcast(session_id, "building", "Clarification timed out — proceeding with best-effort context…")
            finally:
                _pending_clarification.pop(session_id, None)
        else:
            await _broadcast(session_id, "building", "Intent clear — no clarification needed")

        # ── 3. Idea builder ───────────────────────────────────────────────────
        await _broadcast(session_id, "building", "Starting idea builder…")

        async def status_relay(msg: str) -> None:
            await _broadcast(session_id, "building", msg)

        full_intent = intent_text
        if extra_context:
            full_intent = f"{intent_text}\n\n--- Clarifications ---\n{extra_context}"

        blueprint, additional_analyses = await build_ideas(full_intent, session_id=session_id, on_status=status_relay)

        # ── 4. Roadmap creator ────────────────────────────────────────────────
        await _broadcast(session_id, "planning", "Starting roadmap creator…")
        sprints = await create_roadmap(blueprint, on_status=status_relay)

        await _deliver_sprint_graph(session_id, blueprint, sprints, full_intent, intent_kind)

    except asyncio.CancelledError:
        await _broadcast(session_id, "cancelled", "Pipeline cancelled")
        raise
    except Exception as exc:
        logger.exception("Pipeline failed for session %s", session_id)
        await manager.broadcast(
            {
                "type": "error",
                "payload": {"detail": str(exc), "session_id": session_id},
                "session_id": session_id,
                "timestamp": _now(),
            },
            client_type="dashboard",
        )
    finally:
        _active.pop(session_id, None)


async def _deliver_sprint_graph(
    session_id: str,
    blueprint: dict,
    sprints: list,
    intent_text: str,
    intent_kind: str,
) -> None:
    await manager.broadcast(
        {
            "type": "sprint_graph",
            "payload": {
                "session_id": session_id,
                "blueprint": blueprint,
                "sprints": sprints,
                "intent": intent_text,
                "intent_kind": intent_kind,
            },
            "session_id": session_id,
            "timestamp": _now(),
        },
        client_type="dashboard",
    )
    total_h = sum(s.get("estimated_hours", 0) for s in sprints)
    await _broadcast(
        session_id,
        "ready",
        f"{len(sprints)} sprints · {total_h:.1f}h estimated — awaiting approval",
    )


def start(session_id: str, intent_text: str) -> None:
    """Launch the planning pipeline as a background task."""
    cancel(session_id)
    task = asyncio.create_task(_run_pipeline(session_id, intent_text))
    _active[session_id] = task


def cancel(session_id: str) -> bool:
    """Cancel an active pipeline. Returns True if one was running."""
    task = _active.pop(session_id, None)
    if task and not task.done():
        task.cancel()
        return True
    return False


def inject_interrupt(session_id: str, constraint: str) -> None:
    cancel(session_id)
    from backend.exec_pipeline import cancel_execution
    cancel_execution(session_id)


def resolve_clarification(session_id: str, answers: list[dict]) -> bool:
    """Called by main.py when the user submits clarification answers."""
    fut = _pending_clarification.get(session_id)
    if fut and not fut.done():
        fut.set_result(answers)
        return True
    return False


def resolve_improve(session_id: str, feedback: str) -> bool:
    """Called by main.py when the user submits improve feedback for a sprint."""
    fut = _pending_improve.get(session_id)
    if fut and not fut.done():
        fut.set_result(feedback)
        return True
    return False


async def restart_with_improve(session_id: str, sprint_id: int, feedback: str, current_intent: str) -> None:
    """Cancel current pipeline and rerun with improve feedback injected as extra context."""
    cancel(session_id)
    extra = f"[Sprint {sprint_id} improvement request]\n{feedback}"
    task = asyncio.create_task(_run_pipeline(session_id, current_intent, extra_context=extra))
    _active[session_id] = task
