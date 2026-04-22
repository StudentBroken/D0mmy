#!/usr/bin/env python3
"""
D0mmy project manager — run multiple repos simultaneously on separate ports.

Each project gets:
  - Its own backend port
  - Its own .env (inherits API key + model IDs from root .env)
  - Its own ChromaDB collection  (data/projects/<name>/chroma/)
  - Its own sprints.json         (data/projects/<name>/sprints.json)
  - .vscode/settings.json in target repo pointing at correct port

Usage:
    python scripts/projects.py add   <name> <repo-path> [--port 8010]
    python scripts/projects.py start <name>
    python scripts/projects.py stop  <name>
    python scripts/projects.py list
    python scripts/projects.py remove <name>
    python scripts/projects.py open  <name>   # open repo in VS Code
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread

D0MMY_ROOT    = Path(__file__).resolve().parent.parent
REGISTRY_PATH = D0MMY_ROOT / "data" / "projects.json"
ROOT_ENV      = D0MMY_ROOT / ".env"
VSIX_PATH     = D0MMY_ROOT / "vscode-extension" / "d0mmy-vscode-0.1.0.vsix"

# Keys inherited from root .env into every project .env
_INHERITED = {
    "GOOGLE_API_KEY",
    "HEAVY_MODEL",
    "WORKER_MODEL",
    "DAEMON_MODEL",
    "EMBEDDING_MODEL",
    "LOG_LEVEL",
}


# ── Registry helpers ───────────────────────────────────────────────────────────

def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _save_registry(reg: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2) + "\n")


def _load_env(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    if not path.exists():
        return pairs
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            pairs[k.strip()] = v.strip()
    return pairs


def _write_env(path: Path, pairs: dict[str, str]) -> None:
    lines: list[str] = []
    for k, v in pairs.items():
        lines.append(f"{k}={v}\n")
    path.write_text("".join(lines))


def _merge_vscode_json(path: Path, updates: dict) -> None:
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    existing.update(updates)
    path.write_text(json.dumps(existing, indent=2) + "\n")


def _next_free_port(reg: dict) -> int:
    used = {int(p["port"]) for p in reg.values() if "port" in p}
    port = 8010
    while port in used or port == 8000 or port == 8001:
        port += 1
    return port


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _read_pid(pid_file: Path) -> int | None:
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except ValueError:
            pass
    return None


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_add(name: str, repo_str: str, port: int | None) -> None:
    reg = _load_registry()
    if name in reg:
        print(f"  ERROR: project '{name}' already exists. Use 'remove' first.", file=sys.stderr)
        sys.exit(1)

    repo = Path(repo_str).expanduser().resolve()
    if not repo.is_dir():
        print(f"  ERROR: not a directory: {repo}", file=sys.stderr)
        sys.exit(1)

    assigned_port = port if port else _next_free_port(reg)

    # Project data dir
    proj_dir = D0MMY_ROOT / "data" / "projects" / name
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Build per-project .env
    root_pairs = _load_env(ROOT_ENV)
    proj_pairs: dict[str, str] = {k: v for k, v in root_pairs.items() if k in _INHERITED}
    proj_pairs["TARGET_REPO"]        = str(repo)
    proj_pairs["BACKEND_PORT"]       = str(assigned_port)
    proj_pairs["BACKEND_HOST"]       = "127.0.0.1"
    proj_pairs["CHROMA_PERSIST_DIR"] = str(proj_dir / "chroma")
    proj_pairs["SPRINTS_PATH"]       = str(proj_dir / "sprints.json")
    env_file = proj_dir / ".env"
    _write_env(env_file, proj_pairs)

    # Fresh sprints
    sprints_file = proj_dir / "sprints.json"
    sprints_file.write_text("{}\n")

    # .vscode in target repo
    vscode_dir = repo / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    _merge_vscode_json(
        vscode_dir / "settings.json",
        {"d0mmy.backendUrl": f"ws://localhost:{assigned_port}"},
    )
    ext_path = vscode_dir / "extensions.json"
    ext_data: dict = {}
    if ext_path.exists():
        try:
            ext_data = json.loads(ext_path.read_text())
        except json.JSONDecodeError:
            pass
    recs: list[str] = ext_data.get("recommendations", [])
    if "d0mmy.d0mmy-vscode" not in recs:
        recs.append("d0mmy.d0mmy-vscode")
    ext_data["recommendations"] = recs
    ext_path.write_text(json.dumps(ext_data, indent=2) + "\n")

    # Registry entry
    reg[name] = {
        "repo":     str(repo),
        "port":     assigned_port,
        "env_file": str(env_file),
        "proj_dir": str(proj_dir),
        "pid_file": str(proj_dir / "backend.pid"),
    }
    _save_registry(reg)

    print(f"""
  Added project '{name}'
    Repo : {repo}
    Port : {assigned_port}
    Env  : {env_file}

  To start:
    python scripts/projects.py start {name}
""")


def cmd_start(name: str) -> None:
    reg = _load_registry()
    if name not in reg:
        print(f"  ERROR: unknown project '{name}'. Run 'add' first.", file=sys.stderr)
        sys.exit(1)

    p = reg[name]
    pid_file = Path(p["pid_file"])
    existing_pid = _read_pid(pid_file)
    if existing_pid and _pid_alive(existing_pid):
        print(f"  '{name}' already running (PID {existing_pid}, port {p['port']}).")
        return

    env_file = Path(p["env_file"])
    proj_dir  = Path(p["proj_dir"])
    port      = p["port"]

    # Override SPRINTS_PATH via env so exec_pipeline reads project sprints
    env = {
        **os.environ,
        "PYTHONPATH":      str(D0MMY_ROOT),
        "PYTHONUNBUFFERED": "1",
        "D0MMY_ENV_FILE":  str(env_file),
    }
    # pydantic-settings picks up env_file from ENV var if we patch it
    # We pass the env_file path via the --env-file uvicorn flag (not native) instead:
    # Easiest: write a temp launcher env that sets DOTENV_PATH — but cleanest is
    # to just pass env vars directly from the project .env.
    proj_pairs = _load_env(env_file)
    env.update(proj_pairs)

    uv = shutil.which("uv")
    cmd = (
        [uv, "run", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(port)]
        if uv else
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(port)]
    )

    log_file = proj_dir / "backend.log"
    log_fh   = log_file.open("a")

    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=str(D0MMY_ROOT),
        env=env,
        preexec_fn=None if sys.platform == "win32" else os.setsid,
    )
    pid_file.write_text(str(proc.pid))

    # Brief pause to detect immediate crash
    time.sleep(1.5)
    if proc.poll() is not None:
        print(f"  ERROR: backend for '{name}' exited immediately. Check {log_file}", file=sys.stderr)
        pid_file.unlink(missing_ok=True)
        sys.exit(1)

    print(f"""
  Started '{name}'
    PID  : {proc.pid}
    Port : {port}
    Logs : {log_file}
    URL  : http://localhost:{port}
""")


def cmd_stop(name: str) -> None:
    reg = _load_registry()
    if name not in reg:
        print(f"  ERROR: unknown project '{name}'.", file=sys.stderr)
        sys.exit(1)

    pid_file = Path(reg[name]["pid_file"])
    pid = _read_pid(pid_file)
    if not pid or not _pid_alive(pid):
        print(f"  '{name}' is not running.")
        pid_file.unlink(missing_ok=True)
        return

    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        os.kill(pid, signal.SIGTERM)

    # Wait up to 5s
    for _ in range(10):
        time.sleep(0.5)
        if not _pid_alive(pid):
            break

    pid_file.unlink(missing_ok=True)
    print(f"  Stopped '{name}' (was PID {pid}).")


def cmd_list() -> None:
    reg = _load_registry()
    if not reg:
        print("  No projects registered. Use 'add' to create one.")
        return

    print(f"\n  {'NAME':<20} {'PORT':<8} {'STATUS':<12} REPO")
    print(f"  {'-'*20} {'-'*8} {'-'*12} {'-'*40}")
    for name, p in reg.items():
        pid_file = Path(p["pid_file"])
        pid = _read_pid(pid_file)
        status = "running" if (pid and _pid_alive(pid)) else "stopped"
        print(f"  {name:<20} {p['port']:<8} {status:<12} {p['repo']}")
    print()


def cmd_remove(name: str) -> None:
    reg = _load_registry()
    if name not in reg:
        print(f"  ERROR: unknown project '{name}'.", file=sys.stderr)
        sys.exit(1)

    # Stop if running
    pid_file = Path(reg[name]["pid_file"])
    pid = _read_pid(pid_file)
    if pid and _pid_alive(pid):
        cmd_stop(name)

    proj_dir = Path(reg[name]["proj_dir"])
    if proj_dir.exists():
        shutil.rmtree(proj_dir)

    del reg[name]
    _save_registry(reg)
    print(f"  Removed project '{name}'.")


def cmd_open(name: str) -> None:
    reg = _load_registry()
    if name not in reg:
        print(f"  ERROR: unknown project '{name}'.", file=sys.stderr)
        sys.exit(1)
    repo = reg[name]["repo"]
    code = shutil.which("code")
    if not code:
        print(f"  'code' CLI not found. Open manually: {repo}")
        return
    subprocess.Popen([code, repo])
    print(f"  Opening {repo} in VS Code.")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="D0mmy multi-project manager.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Register a new project.")
    p_add.add_argument("name", help="Short project name (slug).")
    p_add.add_argument("repo", help="Path to the target repository.")
    p_add.add_argument("--port", type=int, default=None, help="Backend port (auto-assigned if omitted).")

    p_start = sub.add_parser("start", help="Start a project's backend.")
    p_start.add_argument("name")

    p_stop = sub.add_parser("stop", help="Stop a project's backend.")
    p_stop.add_argument("name")

    sub.add_parser("list", help="List all projects and their status.")

    p_rm = sub.add_parser("remove", help="Remove a project (stops it, deletes data dir).")
    p_rm.add_argument("name")

    p_open = sub.add_parser("open", help="Open project repo in VS Code.")
    p_open.add_argument("name")

    args = parser.parse_args()

    if args.cmd == "add":
        cmd_add(args.name, args.repo, args.port)
    elif args.cmd == "start":
        cmd_start(args.name)
    elif args.cmd == "stop":
        cmd_stop(args.name)
    elif args.cmd == "list":
        cmd_list()
    elif args.cmd == "remove":
        cmd_remove(args.name)
    elif args.cmd == "open":
        cmd_open(args.name)


if __name__ == "__main__":
    main()
