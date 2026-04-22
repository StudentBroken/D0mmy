from __future__ import annotations
import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def call_model(
    role: str,
    messages: list[dict],
    schema: dict | None = None,
    agent: str = "",
    goal: str = "",
) -> dict:
    from backend.models.google import call_google, _role_to_model
    from backend.ws_manager import manager

    call_id = uuid.uuid4().hex[:8]
    model_id = _role_to_model(role)
    t_start = time.monotonic()

    await manager.broadcast(
        {
            "type": "api_call",
            "payload": {
                "call_id": call_id,
                "agent": agent or role,
                "role": role,
                "model": model_id,
                "goal": goal,
                "status": "start",
            },
            "session_id": "system",
            "timestamp": _now(),
        },
        client_type="dashboard",
    )

    try:
        result = await call_google(role=role, messages=messages, schema=schema)
        duration_ms = int((time.monotonic() - t_start) * 1000)

        await manager.broadcast(
            {
                "type": "api_call",
                "payload": {
                    "call_id": call_id,
                    "agent": agent or role,
                    "role": role,
                    "model": model_id,
                    "goal": goal,
                    "status": "complete",
                    "duration_ms": duration_ms,
                    "token_in": result.get("token_in", 0),
                    "token_out": result.get("token_out", 0),
                },
                "session_id": "system",
                "timestamp": _now(),
            },
            client_type="dashboard",
        )

        return result
    except Exception as exc:
        duration_ms = int((time.monotonic() - t_start) * 1000)
        await manager.broadcast(
            {
                "type": "api_call",
                "payload": {
                    "call_id": call_id,
                    "agent": agent or role,
                    "role": role,
                    "model": model_id,
                    "goal": goal,
                    "status": "error",
                    "duration_ms": duration_ms,
                    "error": str(exc)[:200],
                },
                "session_id": "system",
                "timestamp": _now(),
            },
            client_type="dashboard",
        )
        raise
