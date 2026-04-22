"""
Settings API — read and write .env through the dashboard.
GET  /settings        → current config (API key masked)
PUT  /settings        → write key/value pairs to .env, reload config
GET  /settings/bom    → data/bom.json
PUT  /settings/bom    → overwrite data/bom.json
"""

from __future__ import annotations
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/settings", tags=["settings"])

_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"
_BOM_FILE = _ROOT / "data" / "bom.json"

_ALLOWED_KEYS = {
    "GOOGLE_API_KEY",
    "HEAVY_MODEL",
    "WORKER_MODEL",
    "DAEMON_MODEL",
    "EMBEDDING_MODEL",
    "PROJECT_MODE",
    "BACKEND_HOST",
    "BACKEND_PORT",
    "CHROMA_PERSIST_DIR",
    "TARGET_REPO",
    "SPRINTS_PATH",
    "LOG_LEVEL",
}


def _read_env() -> dict[str, str]:
    if not _ENV_FILE.exists():
        return {}
    pairs: dict[str, str] = {}
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            pairs[k.strip()] = v.strip()
    return pairs


def _write_env(pairs: dict[str, str]) -> None:
    lines = ["# D0mmy — managed by settings API\n"]
    for k, v in pairs.items():
        lines.append(f"{k}={v}\n")
    _ENV_FILE.write_text("".join(lines))


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


@router.get("")
async def get_settings() -> dict:
    pairs = _read_env()
    masked = dict(pairs)
    if "GOOGLE_API_KEY" in masked and masked["GOOGLE_API_KEY"]:
        masked["GOOGLE_API_KEY"] = _mask(masked["GOOGLE_API_KEY"])
    return {"settings": masked, "env_file": str(_ENV_FILE), "exists": _ENV_FILE.exists()}


class SettingsUpdate(BaseModel):
    updates: dict[str, str]


_MASKED_KEYS = {"GOOGLE_API_KEY"}


@router.put("")
async def update_settings(body: SettingsUpdate) -> dict:
    unknown = set(body.updates) - _ALLOWED_KEYS
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown keys: {sorted(unknown)}")

    pairs = _read_env()
    skipped = []
    for k, v in body.updates.items():
        if k in _MASKED_KEYS and "*" in v:
            skipped.append(k)
            continue
        pairs[k] = v
    _write_env(pairs)

    # Invalidate cached config so next call re-reads .env
    from backend.config import get_settings as _cfg
    _cfg.cache_clear()

    return {"saved": [k for k in body.updates if k not in skipped], "skipped": skipped}


_VALID_MODES = {"software", "hardware+software"}


@router.get("/mode")
async def get_mode() -> dict:
    pairs = _read_env()
    return {"project_mode": pairs.get("PROJECT_MODE", "software")}


class ModeUpdate(BaseModel):
    project_mode: str


@router.put("/mode")
async def set_mode(body: ModeUpdate) -> dict:
    if body.project_mode not in _VALID_MODES:
        raise HTTPException(status_code=422, detail=f"project_mode must be one of {sorted(_VALID_MODES)}")
    pairs = _read_env()
    pairs["PROJECT_MODE"] = body.project_mode
    _write_env(pairs)
    from backend.config import get_settings as _cfg
    _cfg.cache_clear()
    return {"project_mode": body.project_mode}


@router.get("/bom")
async def get_bom() -> Any:
    if not _BOM_FILE.exists():
        return {}
    try:
        return json.loads(_BOM_FILE.read_text())
    except json.JSONDecodeError:
        return {}


class BomUpdate(BaseModel):
    bom: Any  # accept dict, list, or any valid JSON structure


@router.put("/bom")
async def update_bom(body: BomUpdate) -> dict:
    if body.bom is None:
        raise HTTPException(status_code=422, detail="bom field is required")
    _BOM_FILE.parent.mkdir(parents=True, exist_ok=True)
    _BOM_FILE.write_text(json.dumps(body.bom, indent=2))
    return {"saved": True, "size": len(json.dumps(body.bom))}
