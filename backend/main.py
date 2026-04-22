from __future__ import annotations
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.ws_manager import manager, ClientType
from backend.memory.hdd import store, fetch_context
from backend.memory.ram import scratchpads
from backend.agents.version_oracle import resolve_many, VerifiedRef
from backend.settings_api import router as settings_router
from backend.index_api import router as index_router
from backend.terminal import terminal_endpoint

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)


async def _verify_configured_models() -> None:
    """
    On startup, run every configured model ID through the Version Oracle.
    Logs a warning for any that cannot be verified — never blocks startup,
    but makes stale/hallucinated names visible immediately.
    """
    cfg = get_settings()
    names = {
        "HEAVY_MODEL": cfg.heavy_model,
        "WORKER_MODEL": cfg.worker_model,
        "DAEMON_MODEL": cfg.daemon_model,
        "EMBEDDING_MODEL": cfg.embedding_model,
    }
    logger.info("Version Oracle: verifying %d configured model IDs…", len(names))
    refs = await resolve_many(list(names.values()))

    for env_key, model_id in names.items():
        ref: VerifiedRef = refs[model_id]
        if ref.verified:
            if ref.canonical != model_id:
                logger.warning(
                    "Version Oracle: %s=%s → canonical is '%s'. "
                    "Consider updating your .env. Source: %s",
                    env_key, model_id, ref.canonical, ref.source,
                )
            else:
                logger.info("Version Oracle: %s=%s ✓ verified", env_key, model_id)
        else:
            logger.warning(
                "Version Oracle: %s=%s could NOT be verified. %s",
                env_key, model_id, ref.notes,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _verify_configured_models()
    yield


app = FastAPI(title="D0mmy Orchestrator", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings_router)
app.include_router(index_router)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ack(session_id: str, ref_type: str) -> dict:
    return {
        "type": "ack",
        "payload": {"ref_type": ref_type},
        "session_id": session_id,
        "timestamp": _now(),
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "clients": manager.active}


@app.get("/verify/{name:path}")
async def verify_reference(name: str) -> dict:
    """
    Resolve any model name, package, or API reference to its current verified form.
    Example: GET /verify/gemini%203.1%20pro
    """
    from backend.agents.version_oracle import resolve
    ref = await resolve(name)
    return ref.to_dict()


@app.websocket("/ws/terminal/{session_id}")
async def terminal_ws(ws: WebSocket, session_id: str) -> None:
    await terminal_endpoint(ws, session_id)


@app.websocket("/ws/{client_type}/{client_id}")
async def websocket_endpoint(
    ws: WebSocket,
    client_type: ClientType,
    client_id: str,
) -> None:
    await manager.connect(client_id, client_type, ws)
    try:
        while True:
            raw = await ws.receive_text()
            import json
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send(client_id, {
                    "type": "error",
                    "payload": {"detail": "Invalid JSON"},
                    "session_id": client_id,
                    "timestamp": _now(),
                })
                continue

            msg_type: str = msg.get("type", "")
            payload: dict = msg.get("payload", {})
            session_id: str = msg.get("session_id", client_id)

            if msg_type == "pong":
                pass  # heartbeat reply — connection is alive
            elif msg_type == "harvest":
                await _handle_harvest(session_id, payload, client_id)
            elif msg_type == "intent":
                await _handle_intent(session_id, payload, client_id)
            elif msg_type == "interrupt":
                await _handle_interrupt(session_id, payload)
            elif msg_type == "sprint_approved":
                await _handle_sprint_approved(session_id, payload)
            elif msg_type == "clarification_answers":
                await _handle_clarification_answers(session_id, payload)
            elif msg_type == "sprint_declined":
                await _handle_sprint_declined(session_id, payload)
            elif msg_type == "sprint_improve":
                await _handle_sprint_improve(session_id, payload)
            elif msg_type == "file_context":
                await _handle_file_context(session_id, payload, client_id)
            elif msg_type == "diff_accepted":
                await _handle_diff_accepted(session_id, payload)
            elif msg_type == "diff_rejected":
                await _handle_diff_rejected(session_id, payload)
            else:
                logger.warning("Unhandled message type: %s", msg_type)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as exc:
        logger.warning("WS connection lost for %s: %s", client_id, exc)
        manager.disconnect(client_id)


async def _handle_harvest(session_id: str, payload: dict, client_id: str) -> None:
    text: str = payload.get("text", "").strip()
    source_url: str = payload.get("url", "")
    if not text:
        return
    doc_id = store(text, metadata={"source": source_url, "session": session_id})
    logger.info("Harvested %d chars from %s → doc_id=%s", len(text), source_url, doc_id)
    await manager.send(client_id, _ack(session_id, "harvest") | {
        "payload": {"doc_id": doc_id, "chars": len(text)}
    })


async def _handle_intent(session_id: str, payload: dict, client_id: str) -> None:
    text: str = payload.get("text", "").strip()
    if not text:
        return
    pad = scratchpads.get(session_id)
    pad.append("user", text)
    asyncio.create_task(pad.maybe_truncate())

    from backend.pipeline import start as start_pipeline
    start_pipeline(session_id, text)


async def _handle_interrupt(session_id: str, payload: dict) -> None:
    constraint: str = payload.get("constraint", "")
    logger.info("INTERRUPT session=%s constraint=%r", session_id, constraint)

    from backend.pipeline import inject_interrupt
    inject_interrupt(session_id, constraint)

    pad = scratchpads.get(session_id)
    pad.append("system", f"[INTERRUPT] Constraint added: {constraint}")

    await manager.broadcast(
        {
            "type": "status_update",
            "payload": {"state": "interrupted", "session_id": session_id, "constraint": constraint},
            "session_id": session_id,
            "timestamp": _now(),
        },
        client_type="dashboard",
    )


async def _handle_sprint_approved(session_id: str, payload: dict) -> None:
    sprint_id: int = payload.get("sprint_id", -1)
    logger.info("Sprint approved: session=%s sprint_id=%d", session_id, sprint_id)
    await manager.broadcast(
        {
            "type": "status_update",
            "payload": {"state": "sprint_running", "sprint_id": sprint_id, "session_id": session_id},
            "session_id": session_id,
            "timestamp": _now(),
        },
        client_type="dashboard",
    )
    from backend.exec_pipeline import start_execution
    start_execution(session_id, sprint_id)


async def _handle_clarification_answers(session_id: str, payload: dict) -> None:
    answers: list[dict] = payload.get("answers", [])
    logger.info("Clarification answers received: session=%s count=%d", session_id, len(answers))
    from backend.pipeline import resolve_clarification
    resolved = resolve_clarification(session_id, answers)
    if not resolved:
        logger.warning("No pending clarification for session %s — answers ignored", session_id)


async def _handle_sprint_declined(session_id: str, payload: dict) -> None:
    sprint_id: int = payload.get("sprint_id", -1)
    logger.info("Sprint declined: session=%s sprint_id=%d", session_id, sprint_id)
    from backend.pipeline import cancel
    cancel(session_id)
    await manager.broadcast(
        {
            "type": "status_update",
            "payload": {"state": "declined", "detail": f"Sprint {sprint_id} declined — pipeline stopped", "session_id": session_id},
            "session_id": session_id,
            "timestamp": _now(),
        },
        client_type="dashboard",
    )


async def _handle_sprint_improve(session_id: str, payload: dict) -> None:
    sprint_id: int = payload.get("sprint_id", -1)
    feedback: str = payload.get("feedback", "").strip()
    intent: str = payload.get("intent", "").strip()
    logger.info("Sprint improve: session=%s sprint_id=%d feedback=%r", session_id, sprint_id, feedback[:80])
    if not feedback:
        return
    from backend.pipeline import restart_with_improve
    await restart_with_improve(session_id, sprint_id, feedback, intent)
    await manager.broadcast(
        {
            "type": "status_update",
            "payload": {"state": "improving", "detail": f"Regenerating Sprint {sprint_id} with feedback…", "session_id": session_id},
            "session_id": session_id,
            "timestamp": _now(),
        },
        client_type="dashboard",
    )


# ── IDE (VS Code extension) handlers ──────────────────────────────────────────

# Latest file context per IDE client — Phase 3 Scout/Coder agents read from here
_ide_context: dict[str, dict] = {}


async def _handle_file_context(session_id: str, payload: dict, client_id: str) -> None:
    _ide_context[client_id] = payload
    logger.debug(
        "file_context: client=%s active=%s line=%s",
        client_id,
        payload.get("active_file"),
        payload.get("cursor_line"),
    )


async def _handle_diff_accepted(session_id: str, payload: dict) -> None:
    file_path: str = payload.get("file_path", "")
    logger.info("Diff accepted: session=%s file=%s", session_id, file_path)
    pad = scratchpads.get(session_id)
    pad.append("system", f"[DIFF ACCEPTED] {file_path}")
    from backend.exec_pipeline import resolve_diff
    resolve_diff(session_id, accepted=True)


async def _handle_diff_rejected(session_id: str, payload: dict) -> None:
    file_path: str = payload.get("file_path", "")
    logger.info("Diff rejected: session=%s file=%s", session_id, file_path)
    pad = scratchpads.get(session_id)
    pad.append("system", f"[DIFF REJECTED] {file_path}")
    from backend.exec_pipeline import resolve_diff
    resolve_diff(session_id, accepted=False)
