from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path

from backend.models.client import call_model
from backend.memory.rom import get_prompt, get_schema
from backend.memory.hdd import fetch_context
from backend.agents.module_indexer.index_writer import INDEX_MD

logger = logging.getLogger(__name__)

_BOM_PATH = Path(__file__).resolve().parents[2] / "data" / "bom.json"


def load_bom() -> dict:
    if not _BOM_PATH.exists():
        return {}
    return json.loads(_BOM_PATH.read_text())


async def _tech_harvester(intent: str, context_docs: list[dict], repo_map: str = "") -> dict:
    context_text = "\n\n".join(
        f"[Source: {d['metadata'].get('source', 'local')}]\n{d['text']}"
        for d in context_docs
    )
    if repo_map:
        context_text = f"--- EXISTING PROJECT STRUCTURE ---\n{repo_map}\n\n" + context_text

    result = await call_model(
        role="worker",
        messages=[
            {"role": "system", "content": get_prompt("tech_harvester")},
            {"role": "user", "content": f"Intent: {intent}\n\nContext documents:\n{context_text}"},
        ],
        schema=get_schema("tech_report"),
        agent="tech_harvester",
        goal="Extract technology stack and dependencies from context",
    )
    return result.get("parsed") or {}


async def _rubric_aligner(intent: str, bom: dict) -> dict:
    result = await call_model(
        role="worker",
        messages=[
            {"role": "system", "content": get_prompt("rubric_aligner")},
            {"role": "user", "content": f"Intent: {intent}\n\nHardware BOM:\n{json.dumps(bom, indent=2)}"},
        ],
        schema=get_schema("rubric"),
        agent="rubric_aligner",
        goal="Align hardware BOM against intent requirements",
    )
    return result.get("parsed") or {}


async def _risk_assassin(intent: str, bom: dict, rubric: dict) -> dict:
    result = await call_model(
        role="worker",
        messages=[
            {"role": "system", "content": get_prompt("risk_assassin")},
            {"role": "user", "content": (
                f"Intent: {intent}\n\n"
                f"Hardware BOM:\n{json.dumps(bom, indent=2)}\n\n"
                f"Rubric Report:\n{json.dumps(rubric, indent=2)}"
            )},
        ],
        schema=get_schema("risks"),
        agent="risk_assassin",
        goal="Enumerate hardware failure modes and mitigations",
    )
    return result.get("parsed") or {}


async def _emit(on_status, msg: str) -> None:
    if on_status is None:
        return
    import asyncio
    result = on_status(msg)
    if asyncio.iscoroutine(result):
        await result


async def run(intent: str, session_id: str = "", on_status=None) -> tuple[dict, list[dict]]:
    """
    Map phase: run worker agents → coordinator (may spawn extra Gemma 4 agents) → synthesize.
    Returns (blueprint_dict, additional_analyses_list).
    """
    from backend.config import get_settings
    from backend.agents.coordinator import coordinate
    hardware_mode = get_settings().project_mode == "hardware+software"

    bom = load_bom() if hardware_mode else {}

    # Load local project map if indexed
    repo_map = ""
    if INDEX_MD.exists():
        repo_map = INDEX_MD.read_text(encoding="utf-8", errors="replace")
        # Cap at 15k chars for planning safety; Phase 3 execution handles full file reads
        if len(repo_map) > 15000:
            repo_map = repo_map[:15000] + "\n... (project map truncated)"

    await _emit(on_status, "Fetching context from knowledge base…")

    context_docs = fetch_context(intent, n_results=8)

    if on_status:
        await _emit(on_status, "Running parallel analysis agents…")

    if hardware_mode:
        tech_report, rubric = await asyncio.gather(
            _tech_harvester(intent, context_docs, repo_map=repo_map),
            _rubric_aligner(intent, bom),
        )
        if on_status:
            await _emit(on_status, "Enumerating failure modes…")
        risks = await _risk_assassin(intent, bom, rubric)
    else:
        tech_report = await _tech_harvester(intent, context_docs)
        rubric = {}
        risks = {}

    # Coordinator decides if additional Gemma 4 agents are needed
    if on_status:
        await _emit(on_status, "Coordinator reviewing analysis coverage…")
    try:
        additional_analyses = await coordinate(intent, tech_report, rubric, risks, session_id)
        if additional_analyses and on_status:
            await _emit(on_status, f"Dynamic agents returned {len(additional_analyses)} additional analyses…")
    except Exception as exc:
        logger.warning("Coordinator failed (skipping): %s", exc)
        additional_analyses = []

    if on_status:
        await _emit(on_status, "Synthesizing Application Blueprint (Gemini 3.1 Pro)…")

    synthesis_payload: dict = {
        "intent": intent,
        "tech_report": tech_report,
        "risks": risks,
        "existing_repo_map": repo_map,
    }
    if hardware_mode:
        synthesis_payload["bom"] = bom
        synthesis_payload["rubric"] = rubric
    if additional_analyses:
        synthesis_payload["additional_analyses"] = additional_analyses

    blueprint_result = await call_model(
        role="heavy",
        messages=[
            {"role": "system", "content": get_prompt("blueprint_synthesizer")},
            {"role": "user", "content": json.dumps(synthesis_payload)},
        ],
        schema=get_schema("blueprint"),
        agent="blueprint_synthesizer",
        goal="Synthesize Application Blueprint DAG from all worker reports",
    )

    blueprint = blueprint_result.get("parsed")
    if not blueprint:
        raise RuntimeError(
            f"Blueprint synthesizer failed to return valid JSON. "
            f"Raw output: {blueprint_result.get('content', '')[:500]}"
        )

    logger.info(
        "Blueprint generated: %d nodes, %d edges",
        len(blueprint.get("nodes", [])),
        len(blueprint.get("edges", [])),
    )
    return blueprint, additional_analyses
