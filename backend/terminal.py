"""
Terminal session manager.
Exposes a WebSocket endpoint that gives the dashboard a real shell.
Each message in: {"type": "run"|"input"|"kill"|"resize", ...}
Each message out: {"type": "output"|"started"|"exit"|"error", ...}
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# project root so relative commands like `uv sync` work
_ROOT = str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ENV = {
    **os.environ,
    "TERM": "xterm-256color",
    "FORCE_COLOR": "1",
    "COLORTERM": "truecolor",
    "PYTHONUNBUFFERED": "1",
}


class TerminalSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._process: asyncio.subprocess.Process | None = None
        self._stream_task: asyncio.Task | None = None

    async def run(self, cmd: str, ws: WebSocket) -> None:
        await self.kill()

        await ws.send_text(json.dumps({
            "type": "started",
            "cmd": cmd,
            "ts": datetime.now(timezone.utc).isoformat(),
        }))

        self._process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.PIPE,
            cwd=_ROOT,
            env=_ENV,
        )

        self._stream_task = asyncio.create_task(self._stream(ws))

    async def _stream(self, ws: WebSocket) -> None:
        proc = self._process
        if not proc or not proc.stdout:
            return
        try:
            while True:
                chunk = await proc.stdout.read(1024)
                if not chunk:
                    break
                await ws.send_text(json.dumps({
                    "type": "output",
                    "data": chunk.decode(errors="replace"),
                }))
            code = await proc.wait()
            await ws.send_text(json.dumps({"type": "exit", "code": code}))
        except (ConnectionResetError, RuntimeError):
            pass
        except Exception as exc:
            logger.error("Terminal stream error: %s", exc)

    async def write_stdin(self, data: str) -> None:
        if self._process and self._process.stdin and self._process.returncode is None:
            self._process.stdin.write(data.encode())
            await self._process.stdin.drain()

    async def kill(self) -> None:
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
        proc = self._process
        if proc and proc.returncode is None:
            try:
                if sys.platform == "win32":
                    proc.terminate()
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                proc.kill()
        self._process = None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None


_sessions: dict[str, TerminalSession] = {}


async def terminal_endpoint(ws: WebSocket, session_id: str) -> None:
    await ws.accept()
    session = TerminalSession(session_id)
    _sessions[session_id] = session

    # Send welcome + quick-start commands
    await ws.send_text(json.dumps({
        "type": "output",
        "data": f"\r\n\x1b[32mD0mmy Terminal\x1b[0m  session={session_id}  cwd={_ROOT}\r\n"
               "Type a command and press Run, or use the quick-launch buttons.\r\n\r\n",
    }))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            t = msg.get("type", "")

            if t == "run":
                await session.run(msg.get("cmd", ""), ws)

            elif t == "input":
                await session.write_stdin(msg.get("data", ""))

            elif t == "kill":
                await session.kill()
                await ws.send_text(json.dumps({"type": "killed"}))

            elif t == "ping":
                await ws.send_text(json.dumps({
                    "type": "pong",
                    "running": session.running,
                }))

    except WebSocketDisconnect:
        pass
    finally:
        await session.kill()
        _sessions.pop(session_id, None)
