"""
Phase 3 Execution Pipeline.
Triggered by sprint_approved WS event.
Per approved sprint: Scout → complexity score → dispatch → critic → IDE diff → wait for accept.
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.ws_manager import manager

logger = logging.getLogger(__name__)

def _sprints_path() -> Path:
    from backend.config import get_settings
    p = get_settings().sprints_path
    path = Path(p)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    return path
_DIFF_TIMEOUT  = 300   # seconds to wait for developer Tab/Escape on each diff

# Active execution tasks: session_id → Task
_active: dict[str, asyncio.Task] = {}

# Pending diff acknowledgements: session_id → Future[bool] (True=accepted, False=rejected)
_pending_diff: dict[str, asyncio.Future] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _broadcast(session_id: str, state: str, detail: str = "") -> None:
    await manager.broadcast(
        {
            "type":    "status_update",
            "payload": {"state": state, "detail": detail, "session_id": session_id},
            "session_id": session_id,
            "timestamp": _now(),
        },
        client_type="dashboard",
    )


def _load_sprints() -> dict:
    path = _sprints_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _workspace_root() -> str:
    from backend.config import get_settings
    cfg = get_settings()
    if cfg.target_repo:
        return str(Path(cfg.target_repo).expanduser().resolve())
    return str(_SPRINTS_PATH.resolve().parents[1])


# ── Core execution loop ────────────────────────────────────────────────────────

async def _run_execution(session_id: str, sprint_id: int) -> None:
    from backend.agents.scout import run as scout_run
    from backend.agents.coder.dispatcher import dispatch_node
    from backend.agents.module_indexer import index_files

    data      = _load_sprints()
    blueprint = data.get("blueprint", {})
    sprints   = data.get("sprints", [])

    sprint = next((s for s in sprints if s.get("sprint_id") == sprint_id), None)
    if not sprint:
        await _broadcast(session_id, "error", f"Sprint {sprint_id} not found in sprints.json")
        return

    workspace = _workspace_root()
    node_map  = {n["id"]: n for n in blueprint.get("nodes", [])}
    exec_nodes = [
        node_map[nid]
        for nid in sprint.get("node_ids", [])
        if nid in node_map and node_map[nid].get("type") not in ("hard_stop", "milestone")
    ]

    await _broadcast(session_id, "scouting", f"Sprint {sprint_id}: running scout…")

    try:
        scout_report = await scout_run(sprint, blueprint)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Scout failed for sprint %d", sprint_id)
        await _broadcast(session_id, "error", f"Scout failed: {exc}")
        return

    await _broadcast(
        session_id, "scouting_done",
        f"Scout found {len(scout_report.relevant_modules)} modules, "
        f"{len(scout_report.chroma_hits)} context hits",
    )

    accepted_files: list[str] = []

    for node in exec_nodes:
        label = node.get("label", node.get("id", ""))

        # Check for cancellation between nodes
        if session_id not in _active or _active[session_id].cancelled():
            break

        await _broadcast(session_id, "coding", f"Generating diff: {label}")

        try:
            diff = await dispatch_node(node, scout_report, workspace, session_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("dispatch_node failed for %s", label)
            await _broadcast(session_id, "error", f"Coder failed on '{label}': {exc}")
            continue

        if not diff:
            await _broadcast(session_id, "error", f"No diff produced for '{label}' — skipping")
            continue

        # Broadcast code_diff to all IDE clients
        await manager.broadcast(
            {
                "type": "code_diff",
                "payload": {
                    "file_path":  diff["file_path"],
                    "content":    diff["content"],
                    "summary":    diff.get("summary", ""),
                    "node_label": label,
                    "session_id": session_id,
                },
                "session_id": session_id,
                "timestamp":  _now(),
            },
            client_type="ide",
        )

        await _broadcast(
            session_id, "diff_pending",
            f"Diff ready: {diff['file_path']} — waiting for Tab/Escape in VS Code",
        )

        # Wait for developer accept/reject
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        _pending_diff[session_id] = fut

        try:
            accepted = await asyncio.wait_for(fut, timeout=_DIFF_TIMEOUT)
        except asyncio.TimeoutError:
            await _broadcast(session_id, "diff_timeout", f"Diff timed out — skipping {diff['file_path']}")
            accepted = False
        finally:
            _pending_diff.pop(session_id, None)

        if accepted:
            accepted_files.append(diff["file_path"])
            await _broadcast(session_id, "diff_accepted", f"Accepted: {diff['file_path']}")
        else:
            await _broadcast(session_id, "diff_rejected", f"Rejected: {diff['file_path']}")

    # Re-index accepted files so module index stays current
    if accepted_files:
        try:
            await index_files(accepted_files, workspace)
        except Exception as exc:
            logger.warning("Post-diff re-index failed: %s", exc)

    await _broadcast(
        session_id, "sprint_done",
        f"Sprint {sprint_id} done — {len(accepted_files)}/{len(exec_nodes)} diffs accepted",
    )
    _active.pop(session_id, None)


# ── Public API ─────────────────────────────────────────────────────────────────

def start_execution(session_id: str, sprint_id: int) -> None:
    """Launch execution pipeline as a background asyncio task."""
    cancel_execution(session_id)
    task = asyncio.create_task(_run_execution(session_id, sprint_id))
    _active[session_id] = task


def cancel_execution(session_id: str) -> bool:
    task = _active.pop(session_id, None)
    if task and not task.done():
        task.cancel()
        return True
    return False


def resolve_diff(session_id: str, accepted: bool) -> bool:
    """Called by main.py when IDE sends diff_accepted or diff_rejected."""
    fut = _pending_diff.get(session_id)
    if fut and not fut.done():
        fut.set_result(accepted)
        return True
    return False
