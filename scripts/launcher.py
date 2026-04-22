#!/usr/bin/env python3
from __future__ import annotations
"""
D0mmy Launcher — tiny HTTP server on port 8001.
Manages the uvicorn backend process so the dashboard can start/stop it.

Usage:
    python scripts/launcher.py

Then click "Start Backend" in the dashboard.
"""

import json
import os
import subprocess
import sys
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parent.parent
PORT = 8001
_process: subprocess.Popen | None = None
_log_lines: list[str] = []
_MAX_LOG = 500


def _is_running() -> bool:
    return _process is not None and _process.poll() is None


def _stream_logs(proc: subprocess.Popen, label: str = "backend") -> None:
    for line in proc.stdout:  # type: ignore[union-attr]
        decoded = line.decode(errors="replace").rstrip()
        _log_lines.append(decoded)
        if len(_log_lines) > _MAX_LOG:
            _log_lines.pop(0)
        print(f"[{label}] {decoded}", flush=True)


def _get_uv_backend_cmd() -> list[str]:
    """Return the best command to start the backend."""
    import shutil
    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "uvicorn", "backend.main:app",
                "--reload", "--host", "127.0.0.1", "--port", "8000"]
    return [sys.executable, "-m", "uvicorn", "backend.main:app",
            "--reload", "--host", "127.0.0.1", "--port", "8000"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # silence access logs

    def _respond(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        global _process

        if self.path == "/start":
            if _is_running():
                self._respond(200, {"status": "already_running", "pid": _process.pid})
                return
            env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUNBUFFERED": "1"}
            _process = subprocess.Popen(
                _get_uv_backend_cmd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(ROOT),
                env=env,
                preexec_fn=None if sys.platform == "win32" else os.setsid
            )
            Thread(target=_stream_logs, args=(_process,), daemon=True).start()
            self._respond(200, {"status": "started", "pid": _process.pid})

        elif self.path == "/stop":
            if _is_running():
                try:
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(_process.pid), signal.SIGTERM)
                    else:
                        _process.terminate()
                    _process.wait(timeout=5)
                except Exception:
                    if _process:
                        _process.kill()
                self._respond(200, {"status": "stopped"})
            else:
                self._respond(200, {"status": "not_running"})

        elif self.path == "/restart":
            if _is_running():
                _process.terminate()
                _process.wait(timeout=5)
            # Start fresh
            self.path = "/start"
            self.do_GET()

        elif self.path == "/status":
            self._respond(200, {
                "running": _is_running(),
                "pid": _process.pid if _is_running() else None,
            })

        elif self.path == "/sync":
            import shutil
            uv = shutil.which("uv")
            if not uv:
                self._respond(500, {"error": "uv not found in path"})
                return

            def _run_sync():
                print("[launcher] Running uv sync…", flush=True)
                sync_proc = subprocess.Popen(
                    [uv, "sync"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(ROOT),
                )
                _stream_logs(sync_proc, label="sync")
                sync_proc.wait()
                print("[launcher] uv sync complete.", flush=True)

            Thread(target=_run_sync, daemon=True).start()
            self._respond(200, {"status": "sync_started"})

        elif self.path.startswith("/logs"):
            n = int(self.path.split("?n=")[-1]) if "?n=" in self.path else 100
            self._respond(200, {"lines": _log_lines[-n:]})

        else:
            self._respond(404, {"error": "not found"})


def main():
    print(f"D0mmy Launcher running on http://localhost:{PORT}")
    print(f"Dashboard: start backend from http://localhost:5173")
    print(f"Press Ctrl+C to stop the launcher (this will also stop the backend).\n")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    server.allow_reuse_address = True

    def _shutdown(sig, frame):
        print("\n[launcher] Shutting down...")
        if _is_running():
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(_process.pid), signal.SIGTERM)
                else:
                    _process.terminate()
                _process.wait(timeout=2)
            except Exception:
                if _process:
                    _process.kill()
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    server.serve_forever()


if __name__ == "__main__":
    main()
