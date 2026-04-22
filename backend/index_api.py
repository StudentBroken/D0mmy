"""
Module Index API
GET  /index           — return current module_index.json
POST /index/run       — run full workspace index (async, streams status)
POST /index/files     — lazy index specific files
GET  /index/module/{id} — get single module entry
DELETE /index/file    — invalidate one file entry (forces re-index on next run)
"""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.agents.module_indexer.index_writer import (
    load_index, get_module_by_id, invalidate_file
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/index", tags=["index"])

_ROOT = Path(__file__).resolve().parent.parent   # project root


def _workspace_root() -> str:
    return str(_ROOT)


# ── GET /index ─────────────────────────────────────────────────────────────────

@router.get("")
async def get_index() -> dict:
    index = load_index()
    return {
        "last_indexed":   index.get("last_indexed"),
        "workspace_root": index.get("workspace_root"),
        "total_files":    len(index.get("files", {})),
        "modules":        index.get("modules", []),
    }


# ── POST /index/run ────────────────────────────────────────────────────────────

class RunIndexRequest(BaseModel):
    force: bool = False
    workspace_root: str | None = None


@router.post("/run")
async def run_index(body: RunIndexRequest, background_tasks: BackgroundTasks) -> dict:
    root = body.workspace_root or _workspace_root()

    async def _run() -> None:
        from backend.agents.module_indexer import index_workspace
        from backend.ws_manager import manager
        from datetime import datetime, timezone

        def _now() -> str:
            return datetime.now(timezone.utc).isoformat()

        await manager.broadcast(
            {"type": "status_update", "payload": {"state": "indexing", "detail": "Module indexer started"}, "session_id": "system", "timestamp": _now()},
            client_type="dashboard",
        )
        try:
            stats = await index_workspace(root, force=body.force)
            await manager.broadcast(
                {"type": "status_update", "payload": {"state": "index_complete", "detail": f"Indexed {stats['indexed']} files → {stats['modules']} modules", **stats}, "session_id": "system", "timestamp": _now()},
                client_type="dashboard",
            )
        except Exception as exc:
            logger.error("index_workspace failed: %s", exc)
            await manager.broadcast(
                {"type": "error", "payload": {"detail": f"Indexing failed: {exc}"}, "session_id": "system", "timestamp": _now()},
                client_type="dashboard",
            )

    background_tasks.add_task(_run)
    return {"status": "started", "workspace_root": root, "force": body.force}


# ── POST /index/files ──────────────────────────────────────────────────────────

class IndexFilesRequest(BaseModel):
    files: list[str]
    workspace_root: str | None = None


@router.post("/files")
async def index_files(body: IndexFilesRequest) -> dict:
    from backend.agents.module_indexer import index_files as _index_files
    root = body.workspace_root or _workspace_root()
    stats = await _index_files(body.files, root)
    return stats


# ── GET /index/module/{id} ─────────────────────────────────────────────────────

@router.get("/module/{module_id:path}")
async def get_module(module_id: str) -> dict:
    mod = get_module_by_id(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    return mod


# ── DELETE /index/file ─────────────────────────────────────────────────────────

class InvalidateRequest(BaseModel):
    path: str


@router.delete("/file")
async def invalidate_file_entry(body: InvalidateRequest) -> dict:
    invalidate_file(body.path)
    return {"invalidated": body.path}
