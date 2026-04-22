from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone

from backend.models.client import call_model
from backend.memory.rom import get_prompt, get_schema
from backend.ws_manager import manager

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _run_dynamic_agent(agent_id: str, goal: str, focus: str, input_text: str) -> dict:
    """Run a single dynamic Gemma 4 worker agent with a custom goal."""
    system_prompt = (
        f"You are a specialized analysis agent. Your goal: {goal}\n\n"
        f"Focus specifically on: {focus}\n\n"
        f"Produce a concise, technical analysis. Be specific — name concrete technologies, "
        f"patterns, and tradeoffs. Avoid generic advice."
    )
    result = await call_model(
        role="worker",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ],
        agent=f"dynamic_{agent_id}",
        goal=goal,
    )
    return {"id": agent_id, "goal": goal, "analysis": result.get("content", "")}


async def coordinate(
    intent: str,
    tech_report: dict,
    rubric: dict,
    risks: dict,
    session_id: str,
) -> list[dict]:
    """
    Review worker outputs and decide whether to spawn additional Gemma 4 agents.
    Returns list of additional analysis dicts to merge into the synthesis payload.
    """
    summary = json.dumps({
        "intent": intent,
        "tech_report_keys": list(tech_report.keys()) if tech_report else [],
        "rubric_present": bool(rubric),
        "risks_count": len(risks.get("risks", [])) if risks else 0,
        "tech_summary": str(tech_report)[:800],
    })

    result = await call_model(
        role="daemon",
        messages=[
            {"role": "system", "content": get_prompt("coordinator")},
            {"role": "user", "content": summary},
        ],
        schema=get_schema("coordinator"),
        agent="coordinator",
        goal="Decide if additional Gemma 4 analysis agents are needed",
    )

    parsed = result.get("parsed")
    if not parsed or parsed.get("analysis_sufficient", True):
        logger.info("Coordinator: analysis sufficient, no additional agents spawned")
        return []

    agents_to_spawn: list[dict] = parsed.get("spawn_agents", [])
    if not agents_to_spawn:
        return []

    logger.info("Coordinator: spawning %d additional agents", len(agents_to_spawn))

    # Broadcast spawn events so the API Flow panel renders new nodes
    for spec in agents_to_spawn:
        await manager.broadcast(
            {
                "type": "agent_spawned",
                "payload": {
                    "agent_id": f"dynamic_{spec['id']}",
                    "goal": spec["goal"],
                    "parent": "coordinator",
                    "role": "worker",
                    "model": "gemma-4-31b-it",
                },
                "session_id": session_id,
                "timestamp": _now(),
            },
            client_type="dashboard",
        )

    # Run all spawned agents in parallel
    tasks = [
        _run_dynamic_agent(
            agent_id=spec["id"],
            goal=spec["goal"],
            focus=spec["focus"],
            input_text=spec["input"],
        )
        for spec in agents_to_spawn
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    additional = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Dynamic agent failed: %s", r)
        else:
            additional.append(r)

    return additional
