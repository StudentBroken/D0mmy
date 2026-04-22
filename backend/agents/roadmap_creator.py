from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path

from backend.models.client import call_model
from backend.memory.rom import get_prompt, get_schema

logger = logging.getLogger(__name__)

_SPRINTS_PATH = Path(__file__).resolve().parents[2] / "data" / "sprints.json"


async def _emit(on_status, msg: str) -> None:
    if on_status is None:
        return
    result = on_status(msg)
    if asyncio.iscoroutine(result):
        await result


async def _estimate_times(nodes: list[dict]) -> dict[str, float]:
    """Returns {node_id: estimated_hours}"""
    result = await call_model(
        role="worker",
        messages=[
            {"role": "system", "content": get_prompt("time_estimator")},
            {"role": "user", "content": json.dumps(nodes)},
        ],
        schema=get_schema("time_estimates"),
        agent="time_estimator",
        goal="Estimate hours per task node",
    )
    estimates = result.get("parsed")
    if estimates and isinstance(estimates, list):
        try:
            return {e["id"]: float(e["estimated_hours"]) for e in estimates}
        except (KeyError, ValueError):
            pass
    logger.warning("Time estimator returned unparseable output, using default 2h per node")
    return {n["id"]: 2.0 for n in nodes}


async def _build_sprints(blueprint: dict, time_map: dict[str, float]) -> dict:
    """Intersection Architect — resolves dependencies and creates sprint groups."""
    nodes_with_time = []
    for node in blueprint.get("nodes", []):
        nodes_with_time.append({**node, "estimated_hours": time_map.get(node["id"], 2.0)})

    result = await call_model(
        role="worker",
        messages=[
            {"role": "system", "content": get_prompt("intersection_architect")},
            {"role": "user", "content": json.dumps({
                "nodes": nodes_with_time,
                "edges": blueprint.get("edges", []),
            })},
        ],
        schema=get_schema("sprints"),
        agent="intersection_architect",
        goal="Resolve dependencies and group nodes into sprint batches",
    )
    parsed = result.get("parsed")
    if not parsed:
        raw = result.get("content", "")
        raise RuntimeError(f"Intersection Architect returned invalid JSON: {raw[:300]}")
    return parsed


def _inject_hard_stops(blueprint: dict, sprint_data: dict) -> list[dict]:
    """
    For every sprint ending at a convergence point, ensure a hard_stop node
    is the final node in that sprint. Creates one if missing.
    """
    convergence_ids: set[str] = set(sprint_data.get("convergence_node_ids", []))
    sprints: list[dict] = sprint_data.get("sprints", [])
    node_map: dict[str, dict] = {n["id"]: n for n in blueprint.get("nodes", [])}

    for sprint in sprints:
        if not sprint.get("hard_stop"):
            continue
        node_ids: list[str] = sprint.get("node_ids", [])
        if not node_ids:
            continue
        last_id = node_ids[-1]
        last_node = node_map.get(last_id, {})
        if last_node.get("type") != "hard_stop":
            # Inject a hard stop node
            hs_id = f"hs_{sprint['sprint_id']}"
            hard_stop_node = {
                "id": hs_id,
                "label": f"Hard Stop — Sprint {sprint['sprint_id']} Checkpoint",
                "type": "hard_stop",
                "estimated_hours": 0.5,
                "depends_on": [last_id],
                "agent": "daemon",
            }
            node_map[hs_id] = hard_stop_node
            sprint["node_ids"].append(hs_id)
            sprint["estimated_hours"] = round(
                sum(node_map.get(nid, {}).get("estimated_hours", 0) for nid in sprint["node_ids"]),
                1,
            )
        logger.info("Sprint %d: hard stop at '%s'", sprint["sprint_id"], sprint["node_ids"][-1])

    return sprints


async def run(blueprint: dict, on_status=None) -> list[dict]:
    """
    Reduce phase: estimate times, resolve dependencies, inject hard stops, serialize sprints.
    Returns the sprints array and writes data/sprints.json.
    """
    nodes = blueprint.get("nodes", [])

    await _emit(on_status, "Estimating task durations…")

    time_map = await _estimate_times(nodes)

    await _emit(on_status, "Resolving dependency graph and grouping sprints…")

    sprint_data = await _build_sprints(blueprint, time_map)

    await _emit(on_status, "Injecting Hard Stop testing nodes…")

    sprints = _inject_hard_stops(blueprint, sprint_data)

    # Persist to disk
    _SPRINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SPRINTS_PATH.write_text(json.dumps({
        "blueprint": blueprint,
        "sprints": sprints,
    }, indent=2))

    total_h = sum(s.get("estimated_hours", 0) for s in sprints)
    logger.info(
        "Roadmap created: %d sprints, %.1f total hours, written to %s",
        len(sprints), total_h, _SPRINTS_PATH,
    )
    return sprints
