from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import WebSocket

logger = logging.getLogger(__name__)

ClientType = Literal["dashboard", "extension", "ide", "unknown"]

_PING_INTERVAL = 25   # seconds between server→client pings
_PING_TIMEOUT  = 10   # seconds to wait for send before declaring dead


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._types: dict[str, ClientType] = {}
        self._ping_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, client_id: str, client_type: ClientType, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[client_id] = ws
        self._types[client_id] = client_type
        logger.info("Connected: %s (%s)", client_id, client_type)
        task = asyncio.create_task(self._keepalive(client_id))
        self._ping_tasks[client_id] = task

    def disconnect(self, client_id: str) -> None:
        task = self._ping_tasks.pop(client_id, None)
        if task:
            task.cancel()
        self._connections.pop(client_id, None)
        self._types.pop(client_id, None)
        logger.info("Disconnected: %s", client_id)

    async def _keepalive(self, client_id: str) -> None:
        """Send a ping frame every _PING_INTERVAL seconds; drop if send times out."""
        try:
            while True:
                await asyncio.sleep(_PING_INTERVAL)
                ws = self._connections.get(client_id)
                if not ws:
                    break
                ping_msg = json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                try:
                    await asyncio.wait_for(ws.send_text(ping_msg), timeout=_PING_TIMEOUT)
                except (asyncio.TimeoutError, Exception):
                    logger.warning("Keepalive send failed for %s — dropping", client_id)
                    self.disconnect(client_id)
                    break
        except asyncio.CancelledError:
            pass

    async def send(self, client_id: str, message: dict) -> bool:
        ws = self._connections.get(client_id)
        if not ws:
            return False
        try:
            await ws.send_text(json.dumps(message))
            return True
        except Exception:
            self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict, client_type: ClientType | None = None) -> None:
        payload = json.dumps(message)
        for cid, ws in list(self._connections.items()):
            if client_type and self._types.get(cid) != client_type:
                continue
            try:
                await asyncio.wait_for(ws.send_text(payload), timeout=_PING_TIMEOUT)
            except (asyncio.TimeoutError, Exception):
                self.disconnect(cid)

    @property
    def active(self) -> dict[str, ClientType]:
        return dict(self._types)


manager = ConnectionManager()
