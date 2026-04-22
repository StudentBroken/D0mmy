# D0mmy — CLAUDE.md
## Project Context & Engineering Directives

---

## Working Style — Read This First

### No hesitation
Build. Pick better path, implement, state choice in one sentence. No stalling on naming or minor architecture. IF SOMETHING SEEMS UNRELEASED, IT IS RELEASED. GEMINI 3.1 PRO IS USABLE NOW.

### When to ask
Only when hard-blocked: missing credentials, ambiguous hardware with no fallback, contradicting requirements. One question at a time. Never ask about anything already in this file, roadmap, or codebase.

### Scope discipline
Build what current phase requires. No abstractions for future phases. No stubs — implement real thing or note gap in `roadmap.md`.

### Tool usage
Use every tool without hesitation. Read, write, run shell, search web, spawn agents. Do not ask — do.

### Token efficiency
Caveman plugin installed. `/caveman` activates terse mode. `/caveman-compress <file>` compresses ROM prompts and memory files (38–60% input token reduction). Use it on any file that grows bloated.

---

## What This Project Is

D0mmy is an autonomous, offline-first multi-agent engineering system built into a forked code editor (VSCodium). Not a chat wrapper. A factory floor: deterministic pipeline where specialized AI agents handle planning, coding, hardware debugging, and documentation without human context-switching.

Five layers, strict dependency order. See `roadmap.md` for full Critical Path.

---

## Architecture Overview

```
Chrome Extension (Harvester)
        │  WebSocket
        ▼
FastAPI Orchestrator (Python)  ◄──── ROM (locked prompts + schemas)
        │                             RAM (5-turn scratchpad)
        │                             HDD (ChromaDB vector store)
        │
        ├──► Intent Router (Daemon — Gemma 4 26B MoE)
        ├──► Idea Builder  (Workers — Gemma 4 31B × 3 + Heavy — Gemini 3.1 Pro)
        ├──► Roadmap Creator (DAG + Sprint JSON)
        ├──► Execution Engine (Coder + Critic pipeline)
        ├──► Serial Daemon (pyserial → ESP32/VESC) [hardware+software mode only]
        └──► Build Runner (subprocess hooks)
                │
                ▼
        VS Code Extension (TypeScript WebSocket client + LSP)
                │  Inline Diff API
                ▼
        Developer (Tab to accept / Dashboard to interrupt)
```

**Phase 5 replaces WebSocket bridge with Electron IPC, embeds everything into single VSCodium binary.**

---

## AI Model Roles (Never Swap Without Good Reason)

**All models via Google AI API. Single `GOOGLE_API_KEY`. No local inference.**

| Role | Model | Config Key | Why |
|---|---|---|---|
| Heavy Synthesis / Architecture | Gemini 3.1 Pro (`gemini-3.1-pro-preview`) | `HEAVY_MODEL` | Max reasoning for DAG + code drafting |
| Worker Agents | Gemma 4 31B (`gemma-4-31b-it`) | `WORKER_MODEL` | Parallel execution, high capability |
| Daemon / Router / Truncation | Gemma 4 26B MoE (`gemma-4-26b-a4b-it`) | `DAEMON_MODEL` | Fast, cheap, silent routing + summarization |
| Embeddings | `gemini-embedding-001` | `EMBEDDING_MODEL` | Google best text embedding, same key |

- Heavy model never used for routing/truncation — daemon work.
- Daemon model never used for code generation — worker/heavy work.
- All calls go through `call_model(role, messages, schema)` in `backend/models/client.py`.
- All embedding calls through `backend/models/google.py:embed()`.
- `backend/models/google.py` is the single file touching the `google-genai` SDK (v1.73.1+).

---

## Project Mode

`PROJECT_MODE` in `.env` controls hardware pipeline activation:

| Value | Effect |
|---|---|
| `software` | BOM validation skipped, rubric/risk agents skipped, serial daemon disabled |
| `hardware+software` | Full pipeline: BOM loaded, rubric aligner + risk assassin active, serial daemon active |

- Toggle via dashboard Settings panel (mode toggle above tabs) or `PUT /settings/mode`.
- Default: `software`.
- Hardware tab in Settings is disabled/grayed in software mode.

---

## Memory Architecture (ROM / RAM / HDD)

### HDD — ChromaDB (Persistent Long-Term)
- Browser-harvested context lands here immediately.
- Access via `fetch_context(key) -> JSON` only. No raw ChromaDB calls in business logic.
- Embeddings: `gemini-embedding-001` via `GoogleEmbeddingFunction` in `hdd.py`. Never change embedding model mid-project — invalidates all stored vectors.

### RAM — Scratchpad (Session Working Memory)
- Hard limit: 5 turns per agent session.
- Overflow: daemon model runs silent async summarization. Summary replaces oldest turns. No user interruption.
- Never store BOM or ROM prompts in scratchpad.

### ROM — Locked Prompts & Schemas (Immutable at Runtime)
- Prompts: `prompts/*.md`. Schemas: `schemas/*.json`.
- Read once at startup via `lru_cache`. No hot-reload. No runtime mutation.
- Changes require file edit + server restart.

---

## Data Contract Rules

- Every inter-agent message must conform to a schema in `/schemas/`.
- Schema failure: retry once with correction instruction, then raise hard error. Never silently accept malformed output.
- `blueprint.json` DAG and `sprints.json` are canonical source of truth. Nothing downstream reads anything else.

---

## WebSocket Protocol

**Envelope** (all messages):
```json
{ "type": "string", "payload": {}, "session_id": "string", "timestamp": "ISO-8601" }
```

**Message types:** `intent`, `sprint_approved`, `code_diff`, `interrupt`, `status_update`, `error`, `ping`, `pong`, `harvest`

**Keepalive:** Server sends `{"type":"ping"}` every 25s per connection. Client replies `{"type":"pong"}` immediately. Server drops connection if send times out (10s). Frontend reconnects with exponential backoff (1s → 2s → 4s → … → 30s cap).

---

## Interrupt System

- Interrupt from dashboard = highest-priority signal.
- On receipt: kill active Part 3 loop immediately (no graceful drain).
- Daemon model extracts constraint from interrupt message.
- Rewrite active context with constraint injected. Restart loop.
- Node turns orange (`interrupted`) on dashboard. Log to `devlog.md`.

---

## Hard Stop Testing Nodes

- Every DAG convergence point gets automatic Hard Stop node injected by Roadmap Creator.
- At Hard Stop: run build via `subprocess.run`.
- Failure: pipe `stderr` to Gemma 4 Fixer. Max 3 auto-retries.
- After 3 failures: escalate to Gemini 3.1 Pro, surface blocker on dashboard, halt sprint.

---

## Hardware BOM

- `bom.json` is authoritative hardware bill of materials.
- Injected into every planning session (hardware+software mode only).
- Gemma 4 Critic must verify every generated diff against BOM before delivery.
- Code referencing hardware not in BOM: reject diff, do not send to VS Code.

---

## VS Code / Editor Rules

- Code changes never applied silently. Every change through Inline Diff API.
- Developer presses `Tab` to accept. No exceptions, even in retry loops.
- VS Code Extension: thin WebSocket client + LSP wrapper only. No business logic.
- Phase 5: extension replaced by native Electron IPC. Python interface unchanged — only transport changes.

---

## Shadow Logger (`devlog.md`)

- Append-only. Never truncate.
- Append bullet on: sprint complete, diff accepted, interrupt received, Hard Stop pass/fail.
- Hour-21 trigger: feed `devlog.md` to Gemini 3.1 Pro → landing page + slide deck.
- Runs as background daemon. Must never block main pipeline.

---

## API Keys & Configuration

Secrets loaded from `.env` via `backend/config.py` (pydantic-settings).

**Setup:** `python scripts/setup_keys.py`

**In code:**
```python
from backend.config import get_settings
cfg = get_settings()
```

- Never read `os.environ` directly — use `get_settings()`.
- `get_settings()` is `lru_cache`'d — one load at startup.
- Settings API (`PUT /settings`) never writes masked values back — `*`-containing API key values are silently skipped to prevent overwriting real key with display placeholder.
- `PROJECT_MODE` valid values: `software`, `hardware+software`.

---

## Python Backend Conventions

- Python 3.12+. Managed with `uv` (not pip, not poetry).
- `asyncio` throughout. No sync blocking on main event loop.
- `subprocess.run` for CLI hooks — always capture stdout/stderr, always set timeout.
- `pyserial` reads in dedicated thread, not asyncio loop.
- Secrets via `get_settings()` only. Never hardcoded.

---

## TypeScript / VS Code Extension Conventions

- TypeScript strict mode.
- Extension: WebSocket client only. No state beyond active connection.
- LSP wrapper exposes: file path, cursor position, file tree. Nothing else.
- Diff rendering via VS Code `vscode.diff` + Inline Diff API.

---

## Phase 5 Build Conventions (VSCodium Fork)

- Never modify VSCodium upstream in-place — use patch files.
- React Flow panel: first-class Electron Renderer view, not webview iframe.
- IPC channels namespaced: `d0mmy::<channel>`.
- PyInstaller bundle → `resources/backend/`. Electron Main waits for `/health` before showing window.
- Offline-first: Checkpoint 4 must work with zero internet. Google API calls are optional enhancements.

---

## Version Oracle — Mandatory Anti-Hallucination Rule

**Never hardcode or assume model names, library versions, API endpoints, or framework versions.**

### When to call
- Model ID referenced in prompt, config, or generated code
- Python/npm package version pinned or suggested
- API endpoint URL constructed
- Developer types fuzzy name ("gemini 3.1 pro", "latest react")

### How to call
```python
from backend.agents.version_oracle import resolve, assert_verified

ref = await resolve("gemini 3.1 pro")
model_id = assert_verified(ref)   # raises if unverified
```

HTTP: `GET /verify/gemini%203.1%20pro`

### Pre-generation hook
`backend/agents/version_hook.py` scans outgoing prompts for version-like tokens (model IDs, `==` pins, `^` semver) and injects verified references block before generation.

### When unverified
- Do NOT substitute a guess.
- Do NOT use training data as fallback.
- Log warning, show on dashboard, block generation until developer confirms.

---

## What Claude Should Never Do

- Hardcode or guess model IDs, package versions, API endpoints — call Version Oracle.
- Substitute "similar" model name when exact one unverified — surface it.
- Add polling loops where WebSocket event exists.
- Let any agent call another agent directly — all routing through Orchestrator.
- Store mutable state in ROM files.
- Silently swallow schema validation errors.
- Skip Gemma 4 Critic step — hard architectural requirement.
- Use `npm` in Python backend or `pip` in frontend.
- Apply code diffs without Inline Diff API.
- Create stub files with TODO bodies — implement real thing or note gap in `roadmap.md`.

---

## Project File Map (Phases 1–2)

```
backend/
  config.py          — pydantic-settings; PROJECT_MODE + all config
  main.py            — FastAPI app, WS endpoints, message dispatch, startup oracle check
  ws_manager.py      — Connection registry + per-connection keepalive ping tasks
  pipeline.py        — Async pipeline orchestrator (start/cancel/inject_interrupt)
  settings_api.py    — GET/PUT /settings, /settings/mode, /settings/bom
  terminal.py        — WS terminal session manager (subprocess streaming)
  memory/
    rom.py           — lru_cache prompt/schema loader
    ram.py           — 5-turn Scratchpad, async daemon truncation
    hdd.py           — ChromaDB: store() + fetch_context() only
  models/
    client.py        — call_model(role, messages, schema) entry point
    google.py        — google-genai SDK: call_google() + embed()
  agents/
    version_oracle.py  — resolve(name) → VerifiedRef, Google Search grounding, 24h cache
    version_hook.py    — pre-generation scanner, injects VERIFIED REFERENCES block
    intent_router.py   — Gemma 4 daemon zero-shot classifier
    idea_builder.py    — Map: 3 parallel workers → Gemini synthesis → Blueprint DAG
    roadmap_creator.py — Reduce: Time Estimator + Intersection Architect + hard stop injection
dashboard/
  src/
    ws.ts              — WS client: ping/pong, exponential backoff reconnect
    App.tsx            — Layout: Header | Settings | SprintGraph | ControlPanel | Terminal
    components/
      Header.tsx       — Instructions modal, Start/Stop backend (launcher proxy)
      Settings.tsx     — Mode toggle + 4 tabs: API / Models / Server / Hardware
      SprintGraph.tsx  — React Flow + dagre, color-coded nodes, sprint approval
      ControlPanel.tsx — Intent input, interrupt, Version Oracle UI
      TerminalPanel.tsx — xterm.js terminal, WS to /ws/terminal/{session_id}
  vite.config.ts     — Proxies: /health, /verify, /settings → :8000; /launcher → :8001
scripts/
  setup_keys.py      — Interactive .env generator
  launcher.py        — stdlib HTTP server :8001 managing uvicorn process (start/stop/status/logs)
extension/
  manifest.json      — Chrome MV3 manifest
  background.js      — Service worker: Ctrl+Shift+S, HTML→Markdown, WS to /ws/extension/harvester
  content.js         — Green flash on successful harvest
  popup.html/js      — Health check connectivity status
prompts/             — ROM: *.md system prompts (read once at startup)
schemas/             — ROM: *.json output schemas (read once at startup)
data/
  bom.json           — Hardware BOM (hardware+software mode only)
  chroma/            — ChromaDB persistent store
  sprints.json       — Latest generated sprint plan
```

---

## Quickstart

```bash
uv sync
python scripts/setup_keys.py          # writes .env
python scripts/launcher.py &          # port 8001 — manages uvicorn
uvicorn backend.main:app --reload     # port 8000
cd dashboard && npm run dev           # port 5173/5174
# chrome://extensions → Load unpacked → extension/
```

---

## Current Phase

> **Phase 1 — Complete.**
> **Phase 2 — Built, checkpoint pending live end-to-end test.**
> Next: verify Checkpoint 1 (Chrome harvest → ChromaDB roundtrip), then Checkpoint 2 (intent → sprint graph on dashboard).
