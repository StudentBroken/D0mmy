# D0mmy — Autonomous Multi-Agent Engineering System
## Critical Path Roadmap

> No phase begins until previous phase checkpoint verified.
> All AI inference through single Google AI API key. No local model servers.
> Version Oracle mandatory — no model ID, package version, or API endpoint ever hardcoded.

---

## Stack

| Layer | Technology | Model ID |
|---|---|---|
| Orchestrator | Python 3.12, FastAPI, uvicorn | — |
| Event Bus | WebSockets → Electron IPC (Phase 5) | — |
| Heavy Synthesis | google-genai>=1.73.1 | `gemini-3.1-pro-preview` |
| Worker Agents | google-genai>=1.73.1 | `gemma-4-31b-it` |
| Daemon / Router | google-genai>=1.73.1 | `gemma-4-26b-a4b-it` |
| Embeddings | google-genai `embed_content` | `gemini-embedding-001` |
| Vector DB | ChromaDB (local, Google embeddings) | — |
| Dashboard | Vite + React + @xyflow/react + dagre | — |
| Terminal | xterm.js (@xterm/xterm v5.5) | — |
| Editor Bridge | TypeScript VS Code Extension + LSP | — |
| Serial I/O | pyserial (hardware+software mode only) | — |
| Final Editor | VSCodium (Electron fork) | — |
| Distribution | PyInstaller + VSCodium build | — |

---

## Phase 1 — The Central Nervous System
**Status: COMPLETE**
**Goal: Headless Python Orchestrator + WebSocket event bus + deterministic memory**

### 1.1 FastAPI Backbone
- [x] FastAPI server (headless), uvicorn
- [x] Bidirectional WebSocket at `/ws/{client_type}/{client_id}`
- [x] Connection registry with client type tracking (dashboard/extension/ide)
- [x] JSON envelope: `{type, payload, session_id, timestamp}`
- [x] `/health` endpoint returning active client map
- [x] Per-connection keepalive: server ping every 25s, drops on 10s timeout
- [x] WS frontend: exponential backoff reconnect (1s → 30s cap), auto pong reply
- [x] Generic `Exception` handler on WS endpoint (not just `WebSocketDisconnect`)

### 1.2 AI Integrations (google-genai SDK v1.73.1)
- [x] `google-genai` SDK (replaced deprecated `google-generativeai`)
- [x] `backend/models/google.py` — `call_google(role, messages, schema)`:
  - `"heavy"` → `gemini-3.1-pro-preview`
  - `"worker"` → `gemma-4-31b-it`
  - `"daemon"` → `gemma-4-26b-a4b-it`
- [x] JSON schema enforcement: one auto-retry with correction prompt, then hard error
- [x] `backend/models/client.py` — `call_model()` unified entry point
- [x] `backend/models/google.py:embed()` — `gemini-embedding-001` via `EmbedContentConfig`

### 1.3 Version Oracle (Anti-Hallucination)
- [x] `backend/agents/version_oracle.py` — `resolve(name) -> VerifiedRef`
  - Gemini + Google Search grounding (not training data)
  - `VerifiedRef`: `{canonical, version, kind, verified, source, notes, verified_at}`
  - Unverified → raises or warns, never silently proceeds
  - In-memory cache, 24h TTL
- [x] Startup check: `_verify_configured_models()` logs warnings for stale `.env` IDs
- [x] `GET /verify/{name}` — developer-accessible oracle endpoint
- [x] `backend/agents/version_hook.py` — pre-generation scanner: regex for model IDs, `==` pins, `^` semver; injects `VERIFIED REFERENCES` block into prompts
- [x] Dashboard: Version Oracle UI in ControlPanel (type reference → get canonical + source)

### 1.4 Deterministic Memory (ROM / RAM / HDD)
- [x] **ROM** — `backend/memory/rom.py`: `lru_cache` load of `prompts/*.md` + `schemas/*.json`
- [x] **RAM** — `backend/memory/ram.py`: 5-turn Scratchpad, daemon summarization on overflow
- [x] **HDD** — `backend/memory/hdd.py`: ChromaDB + `GoogleEmbeddingFunction` (gemini-embedding-001). Public API: `store()` + `fetch_context()` only.

### 1.5 Browser Harvester (Chrome Extension MV3)
- [x] Service worker, `Ctrl+Shift+S` / `⌘+Shift+S`
- [x] Selection → HTML → Markdown in service worker
- [x] WS message to `/ws/extension/harvester` → FastAPI → ChromaDB
- [x] Content script: green flash on harvest
- [x] Popup: live `/health` connectivity status

### 1.6 Project Mode
- [x] `PROJECT_MODE` config key: `software` | `hardware+software`
- [x] Software mode: BOM/rubric/risk agents skipped, serial daemon disabled
- [x] Hardware+software mode: full pipeline, BOM validation active
- [x] `GET /settings/mode` + `PUT /settings/mode` endpoints
- [x] Dashboard: mode toggle pill above settings tabs

### 1.7 Settings & Launcher
- [x] `GET/PUT /settings` — reads/writes `.env`, clears `get_settings()` cache
- [x] Masked key protection: `PUT /settings` skips GOOGLE_API_KEY if value contains `*`
- [x] `GET/PUT /settings/bom` — BOM JSON editor
- [x] `scripts/launcher.py` — stdlib HTTP server :8001, manages uvicorn start/stop/status/logs
- [x] Dashboard Settings: 4 tabs (API / Models / Server / Hardware), mode toggle, oracle verify buttons
- [x] xterm.js terminal panel with quick-launch buttons and WS streaming

**CHECKPOINT 1:** Highlight text in Chrome → `Ctrl+Shift+S` → query back:
```python
from backend.memory.hdd import fetch_context
print(fetch_context("your highlighted text"))
# Must return text with cosine distance < 0.1
```
**Status: Built — pending live end-to-end verification**

---

## Phase 2 — The Planning Engine
**Status: BUILT — checkpoint pending live verification**
**Goal: Map-Reduce idea generator + DAG roadmap creator + HITL approval dashboard**

### 2.1 Intent Router & BOM Injection
- [x] `backend/agents/intent_router.py` — Gemma 4 daemon zero-shot classifier
  - Output: `{"intent": "hardware|software|mixed", "confidence": 0.0–1.0}`
  - ROM prompt: `prompts/intent_router.md`, schema: `schemas/intent.json`
- [x] BOM injected only in hardware+software mode

### 2.2 Idea Builder (Map)
- [x] `backend/agents/idea_builder.py` — parallel Gemma 4 Worker agents:
  - **Tech Harvester** — ChromaDB (8 docs) + prior art → `schemas/tech_report.json`
  - **Rubric Aligner** — BOM constraint scoring → `schemas/rubric.json` (hardware mode only)
  - **Risk Assassin** — failure mode enumeration → `schemas/risks.json` (hardware mode only)
  - Tech Harvester + Rubric Aligner parallel; Risk Assassin after Rubric
- [x] Merged output → Gemini 3.1 Pro → `schemas/blueprint.json` (strict enforcement)
- [x] Hardware/software mode gates: software mode runs Tech Harvester only
- [x] `on_status` callback streams progress to dashboard

### 2.3 Roadmap Creator (Reduce)
- [x] `backend/agents/roadmap_creator.py`:
  - **Time Estimator** (Gemma 4 Worker): `estimated_hours` per node
  - **Intersection Architect** (Gemma 4 Worker): dependency resolution, sprint grouping
  - Auto-injects `"type":"hard_stop"` node at every convergence sprint endpoint
  - Writes `data/sprints.json`
- [x] `backend/pipeline.py` — full pipeline: `start()` / `cancel()` / `inject_interrupt()`

### 2.4 Dashboard Visualizer (HITL Gate)
- [x] Vite + React + TypeScript + `@xyflow/react` + `dagre` auto-layout
- [x] `SprintGraph.tsx` — color-coded nodes: `task`=blue, `hard_stop`=crimson, `milestone`=green, `interrupted`=orange; animated running edges
- [x] Per-sprint "Approve ▶" button → `sprint_approved` WS event
- [x] `ControlPanel.tsx` — intent input, interrupt input, Version Oracle panel
- [x] Live status bar from all pipeline steps

**CHECKPOINT 2:** Type intent → ~30s → hardware-constrained sprint graph on dashboard → Approve fires WS event.
**Status: Built — pending live end-to-end verification**

---

## Phase 3 — The Execution Engine
**Status: IN PROGRESS**
**Goal: AI pipeline wired to live codebase via VS Code Extension + LSP**

### 3.0 Module Indexer (Context Pyramid Base)
- [x] `backend/agents/module_indexer/ast_graph.py` — Python AST + TS regex symbol/import extractor with SHA-256 checksum
- [x] `backend/agents/module_indexer/file_summarizer.py` — Gemma 4 Worker per-file TLDR + markdown tree, bounded concurrency (5), cached by checksum
- [x] `backend/agents/module_indexer/module_grouper.py` — Gemma 4 Worker groups files into logical modules using import graph hint; fallback: one-module-per-file
- [x] `backend/agents/module_indexer/index_writer.py` — writes `data/module_index.json` (canonical) + `data/module_index.md` (human-editable view)
- [x] `backend/agents/module_indexer/indexer.py` — `index_workspace(root, force)` lazy full scan + `index_files(paths)` targeted re-index
- [x] `backend/index_api.py` — `GET /index`, `POST /index/run`, `POST /index/files`, `GET /index/module/{id}`, `DELETE /index/file`
- [x] `schemas/file_summary.json`, `schemas/module_group.json`, `prompts/file_summarizer.md`, `prompts/module_grouper.md`

**Index format:** `module_index.json` — JSON outer structure (machine-readable), markdown tree strings as values (LLM-efficient). Heavy model reads module TLDRs + trees, never raw code by default.

**Escalation routing (Phase 3.3):** Gemini scores task complexity 0–10 before dispatch. ≥8 OR Gemma fail ×2 → Gemini direct path with stripped context + tool access.

### 3.1 Scout Handoff
- [x] Trigger on `sprint_approved` WS event → `exec_pipeline.start_execution()`
- [x] Parallel workers in `backend/agents/scout.py`:
  - **RepoSearcher**: ChromaDB semantic query + module_index.json keyword relevance score (no AI)
  - **WebSearcher**: Gemini heavy — research patterns/approaches for sprint task
- [x] `ScoutReport` dataclass: sprint, nodes, relevant_modules, chroma_hits, web_context

### 3.2 VS Code Bridge
- [x] TypeScript VS Code Extension in `vscode-extension/`
- [x] WS client → `/ws/ide/{machine_id}`, exponential backoff reconnect
- [x] LSP wrapper: file path, cursor line/col, workspace file tree
- [x] Bidirectional: receives diffs, sends file context

### 3.3 Surgical Coder Pipeline (Tiered Context Pyramid)
- [x] `backend/agents/coder/complexity_scorer.py` — Gemma daemon scores task 0–10; ≥8 → direct path
- [x] `backend/agents/coder/retriever.py` — disk reads for module files (no AI); cap 6k/file, 20k total
- [x] `backend/agents/coder/module_coder.py` — Gemma 4 Worker; up to 2 attempts; injects scout context
- [x] `backend/agents/coder/gemini_direct.py` — Gemini heavy; escalation path; full file context + prev issues
- [x] `backend/agents/coder/critic.py` — Gemini heavy always reviews; BOM check in hardware mode
- [x] `backend/agents/coder/dispatcher.py` — routes: score → Gemma×2 → escalate → critic → critic retry
- [x] `backend/exec_pipeline.py` — sprint loop: scout → dispatch per node → broadcast code_diff → wait Tab/Esc → re-index accepted files
- [x] VS Code extension sends `diff_accepted`/`diff_rejected` back; exec pipeline future resolves

### 3.4 Delivery Agent (Interrupt System)
- [x] Dashboard interrupt input → `{type:"interrupt", payload:{constraint}}` via WS (ControlPanel)
- [x] `inject_interrupt()` cancels both planning pipeline AND exec_pipeline
- [x] Node turns orange (`interrupted`) via `status_update` broadcast to dashboard

**CHECKPOINT 3:** Approve sprint → AI reads repo via module index → diffs file in VS Code → Tab to accept → interrupt kills exec loop → node turns orange.

**CHECKPOINT 3:** Approve sprint → AI reads repo → diffs file in VS Code → interrupt kills loop cleanly, node turns orange.

---

## Phase 4 — Hardware Daemons & Automated Testing
**Status: NOT STARTED**
**Goal: COM port automation, build system, shadow logging**

### 4.1 Serial Daemon (hardware+software mode only)
- [ ] `backend/daemons/serial_daemon.py` — pyserial in dedicated thread
- [ ] COM port list from `bom.json`
- [ ] Error line detected → pipe + 20 lines context → Gemma 4 Fixer → VS Code diff

### 4.2 Build Runner
- [ ] `backend/build_runner.py` — `subprocess.run` wrappers with timeout
- [ ] Linked to Hard Stop nodes in sprint graph
- [ ] Failure: `stderr` → Gemma 4 Fixer, max 3 retries → escalate to Gemini 3.1 Pro → halt sprint

### 4.3 Shadow Logger & Pitch Generator
- [ ] `backend/daemons/logger_daemon.py` — append-only `data/devlog.md`
  - Events: sprint complete, diff accepted, interrupt, Hard Stop pass/fail
- [ ] Hour-21 trigger (or `/pitch` button): `devlog.md` → Gemini 3.1 Pro → landing page + Marp slides

**CHECKPOINT 4:** Corrupt ESP32 serial output → VS Code presents fix diff within 5 seconds. No human terminal.

---

## Phase 5 — The Ultimate Fork (VSCodium)
**Status: NOT STARTED**
**Goal: Embed entire system into editor binary. One icon, everything boots.**

### 5.1 VSCodium Source Build
- [ ] Clone VSCodium, set up C++/Node/Electron toolchain
- [ ] Verify vanilla build before any modification

### 5.2 Native UI Integration
- [ ] React Flow dashboard → Electron Renderer first-class panel (not webview)
- [ ] IPC namespace: `d0mmy::<channel>`

### 5.3 Native IPC Routing
- [ ] Replace all editor↔Python WS with Electron `ipcMain`/`ipcRenderer`
- [ ] Target sub-millisecond local round-trip

### 5.4 Daemon Hijack
- [ ] Serial listener → Electron Main Process
- [ ] Terminal tracking → Electron Main Process
- [ ] Python Orchestrator retains: Google API, ChromaDB, sprint logic only

### 5.5 Single Executable
- [ ] FastAPI → PyInstaller → `resources/backend/`
- [ ] Electron Main: spawn Python → poll `/health` → show window
- [ ] Verify fully offline operation (Google API = only network dependency)

**FINAL CHECKPOINT:** Single icon → UI + Python + daemons + ChromaDB boot. Fully local. Zero-latency swarm in editor binary.

---

## Critical Path

```
[1.1 FastAPI+WS+Keepalive] ──► [1.2 google-genai SDK] ──► [1.3 Version Oracle]
                                                                    │
                                                          [1.4 ROM/RAM/HDD Memory]
                                                                    │
                                                          [1.5 Chrome Extension]
                                                                    │
                                                          [1.6 Project Mode]
                                                                    │
                                              ┌─────────────────────┘
                                              ▼
                              [2.1 Router+BOM] ──► [2.2 Idea Builder (Map)]
                                                            │
                                                  [2.3 Roadmap Creator (Reduce)]
                                                            │
                                                  [2.4 Dashboard (HITL Gate)]
                                                            │
                              ┌─────────────────────────────┘
                              ▼
          [3.1 Scout] ──► [3.2 VS Code Bridge] ──► [3.3 Coder Pipeline]
                                                            │
                                                  [3.4 Interrupt System]
                                                            │
          ┌─────────────────────────────────────────────────┘
          ▼
[4.1 Serial Daemon] + [4.2 Build Runner] + [4.3 Shadow Logger]
          │
          ▼
[5.1 VSCodium] ──► [5.2 Native UI] ──► [5.3 IPC] ──► [5.4 Daemons] ──► [5.5 Binary]
```

---

## Current Status

| Phase | Status |
|---|---|
| Phase 1 | Complete |
| Phase 2 | Built — live checkpoint pending |
| Phase 3 | Not started |
| Phase 4 | Not started |
| Phase 5 | Not started |

**Next actions:**
1. Load Chrome extension → harvest page → verify `fetch_context()` returns it (Checkpoint 1)
2. Enter intent on dashboard → verify sprint graph renders (Checkpoint 2)
3. Begin Phase 3: VS Code Extension scaffold
