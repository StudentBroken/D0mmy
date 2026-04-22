#!/usr/bin/env python3
"""
Attach D0mmy to an existing repository.

Usage:
    python scripts/attach.py /path/to/your/repo
    python scripts/attach.py /path/to/your/repo --port 8000

What it does:
    1. Sets TARGET_REPO in D0mmy's .env so the backend works against your repo.
    2. Writes .vscode/settings.json in your repo pointing at this D0mmy instance.
    3. Writes .vscode/extensions.json recommending the D0mmy extension.
    4. Clears stale sprints.json so the next run starts clean.
    5. Prints the quickstart.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

D0MMY_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE   = D0MMY_ROOT / ".env"
VSIX_PATH  = D0MMY_ROOT / "vscode-extension" / "d0mmy-vscode-0.1.0.vsix"


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


def _merge_json(path: Path, updates: dict) -> None:
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    existing.update(updates)
    path.write_text(json.dumps(existing, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Attach D0mmy to an existing repo.")
    parser.add_argument("repo", help="Absolute or relative path to the target repository.")
    parser.add_argument("--port", type=int, default=8000, help="D0mmy backend port (default: 8000).")
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Remove TARGET_REPO from .env, resetting D0mmy to self-hosted mode.",
    )
    args = parser.parse_args()

    # ── Detach mode ──────────────────────────────────────────────────────────
    if args.detach:
        pairs = _load_env(ENV_FILE)
        pairs.pop("TARGET_REPO", None)
        _write_env(ENV_FILE, pairs)
        print("\n  D0mmy detached — TARGET_REPO removed from .env.")
        print("  Restart backend: uvicorn backend.main:app --reload\n")
        return

    # ── Resolve target repo ──────────────────────────────────────────────────
    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"\n  ERROR: path does not exist: {repo}", file=sys.stderr)
        sys.exit(1)
    if not repo.is_dir():
        print(f"\n  ERROR: not a directory: {repo}", file=sys.stderr)
        sys.exit(1)

    port = args.port
    ws_base = f"ws://localhost:{port}"

    print(f"\n  Attaching D0mmy → {repo}")

    # ── 1. Update .env ───────────────────────────────────────────────────────
    if not ENV_FILE.exists():
        print(f"\n  ERROR: {ENV_FILE} not found. Run `python scripts/setup_keys.py` first.", file=sys.stderr)
        sys.exit(1)

    pairs = _load_env(ENV_FILE)
    pairs["TARGET_REPO"] = str(repo)
    if port != 8000:
        pairs["BACKEND_PORT"] = str(port)
    _write_env(ENV_FILE, pairs)
    print(f"  [1/4] Updated {ENV_FILE.name} — TARGET_REPO={repo}")

    # ── 2. .vscode/settings.json in target repo ──────────────────────────────
    vscode_dir = repo / ".vscode"
    vscode_dir.mkdir(exist_ok=True)

    settings_path = vscode_dir / "settings.json"
    _merge_json(settings_path, {"d0mmy.backendUrl": ws_base})
    print(f"  [2/4] Wrote {settings_path.relative_to(repo)}")

    # ── 3. .vscode/extensions.json ───────────────────────────────────────────
    ext_path = vscode_dir / "extensions.json"
    existing_ext: dict = {}
    if ext_path.exists():
        try:
            existing_ext = json.loads(ext_path.read_text())
        except json.JSONDecodeError:
            pass
    recs: list[str] = existing_ext.get("recommendations", [])
    if "d0mmy.d0mmy-vscode" not in recs:
        recs.append("d0mmy.d0mmy-vscode")
    existing_ext["recommendations"] = recs
    ext_path.write_text(json.dumps(existing_ext, indent=2) + "\n")
    print(f"  [3/4] Wrote {ext_path.relative_to(repo)}")

    # ── 4. Clear stale sprints ───────────────────────────────────────────────
    sprints_path = D0MMY_ROOT / "data" / "sprints.json"
    if sprints_path.exists():
        sprints_path.write_text("{}\n")
        print(f"  [4/4] Cleared stale sprints.json")
    else:
        sprints_path.parent.mkdir(parents=True, exist_ok=True)
        sprints_path.write_text("{}\n")
        print(f"  [4/4] Created fresh sprints.json")

    # ── Done ─────────────────────────────────────────────────────────────────
    print(f"""
  ✓ D0mmy attached to: {repo}

  Next steps:
    1. Restart backend (picks up new TARGET_REPO):
         uvicorn backend.main:app --reload --port {port}

    2. Open the target repo in VS Code:
         code {repo}

    3. If D0mmy extension not installed:
         code --install-extension {VSIX_PATH}

    4. Open dashboard:
         cd {D0MMY_ROOT}/dashboard && npm run dev

  To detach later:
    python scripts/attach.py {repo} --detach
""")


if __name__ == "__main__":
    main()
