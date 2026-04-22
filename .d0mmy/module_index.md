# Module Index
> Last indexed: 2026-04-22T05:00:08.003738+00:00  |  Workspace: `/Users/xumic/Developer/D0mmy`

---

## `backend/main-entry` — Main Entry
> Main FastAPI application entry point and global routing

**Files:** `backend/main.py`
**Deps:** backend/ws-manager, backend/memory/hdd, backend/memory/ram, backend/agents/version-oracle

```
backend/main.py
├── _verify_configured_models:24 — verifies LLM model IDs on startup
├── lifespan:59 — manages app startup and shutdown
├── _now:77 — returns current UTC timestamp
├── _ack:81 — creates a standardized acknowledgement response
├── health:91 — health check endpoint
├── verify_reference:96 — resolves model/API references via Version Oracle
├── terminal_ws:107 — websocket endpoint for terminal access
├── websocket_endpoint:112 — main websocket router for client messages
├── _handle_harvest:169 — processes incoming content harvesting
├── _handle_intent:181 — processes user intentions
├── _handle_interrupt:193 — handles session interruptions
├── _handle_sprint_approved:214 — handles approved sprint plans
├── _handle_clarification_answers:230 — handles user clarification answers
├── _handle_sprint_declined:239 — handles declined sprint plans
├── _handle_sprint_improve:255 — handles requested sprint improvements
├── _handle_file_context:281 — processes file context updates
├── _handle_diff_accepted:291 — handles accepted code diffs
└── _handle_diff_rejected:300 — handles rejected code diffs
```

---

## `backend/ws-manager` — WebSocket Manager
> Manages real-time client connections, heartbeats, and message broadcasting

**Files:** `backend/ws_manager.py`

```
backend/ws_manager.py
└── ConnectionManager:18 — Manages WebSocket lifecycles and messaging
    ├── connect:24 — Accepts connection and starts keepalive task
    ├── disconnect:32 — Removes client and cancels keepalive
    ├── _keepalive:40 — Periodically pings clients to detect timeouts
    ├── send:61 — Sends a JSON message to a specific client
    ├── broadcast:72 — Sends a JSON message to all or filtered clients
    └── active:83 — Returns a map of active client IDs and types
```

---

## `backend/config` — Configuration
> Application settings management using Pydantic

**Files:** `backend/config.py`
**Deps:** pydantic, pydantic_settings

```
backend/config.py
├── Settings:11 — application configuration settings
│   ├── must_not_be_empty:45 — validates that google_api_key is provided
│   └── derive_project_paths:53 — calculates project-specific data paths
└── get_settings:66 — returns a cached Settings instance
```

---

## `backend/memory/hdd` — Long-term Memory (HDD)
> Vector storage management using ChromaDB and Google embeddings

**Files:** `backend/memory/hdd.py`
**Deps:** chromadb, backend/models/google

```
backend/memory/hdd.py
├── GoogleEmbeddingFunction:20 — ChromaDB embedding function for documents
│   └── __call__:23 — generates embeddings for documents
├── GoogleQueryEmbeddingFunction:28 — ChromaDB embedding function for queries
│   └── __call__:31 — generates embeddings for queries
├── _now:16 — gets current UTC ISO timestamp
├── _client:40 — returns a singleton ChromaDB PersistentClient
├── _collection:52 — returns a singleton ChromaDB Collection
├── store:64 — saves text and metadata to vector storage
├── fetch_context:74 — retrieves top-n similar documents for a query
└── fetch_context_json:152 — retrieves similar documents as a JSON string
```

---

## `backend/memory/ram` — Short-term Memory (RAM)
> Scratchpad memory for session context with automatic summarization

**Files:** `backend/memory/ram.py`
**Deps:** backend/models/client

```
backend/memory/ram.py
├── Turn:13 — Data model for a single conversation turn
├── Scratchpad:19 — Session-specific memory buffer with truncation
│   ├── append:24 — Adds a new turn to memory
│   ├── maybe_truncate:27 — Checks if truncation is needed and triggers it
│   └── _truncate:35 — Summarizes old turns using an AI model
│   └── to_messages:54 — Converts turns to API-compatible message list
└── ScratchpadRegistry:58 — Global registry for session scratchpads
    ├── get:62 — Retrieves or creates a scratchpad for a session
    └── clear:67 — Removes a scratchpad from the registry
```

---

## `backend/memory/rom` — Template Memory (ROM)
> Cached loading of prompt templates and JSON schemas

**Files:** `backend/memory/rom.py`

```
backend/memory/rom.py
├── get_prompt:11 — loads and caches a markdown prompt file
└── get_schema:19 — loads and caches a JSON schema file
```

---

## `backend/models/client` — Model Client
> Unified LLM API caller with integrated monitoring and broadcasting

**Files:** `backend/models/client.py`
**Deps:** backend/models/google, backend/ws-manager

```
backend/models/client.py
├── _now:10 — Returns current UTC time in ISO format
└── call_model:14 — Executes LLM calls and broadcasts status to dashboard
```

---

## `backend/models/google` — Google Gemini Interface
> Interface for Google Gemini API with model selection and retries

**Files:** `backend/models/google.py`
**Deps:** google.genai, backend/agents/version-hook

```
backend/models/google.py
├── _client:16 — cached Google GenAI client instance
├── ensure_configured:20 — validates API configuration
├── _role_to_model:24 — maps role identifiers to specific model IDs
├── _build_contents:33 — converts messages to Gemini contents format
├── _system_instruction:44 — extracts system prompts from messages
├── _clean_json_response:49 — extracts JSON from LLM text output
├── _prune_schema:104 — sanitizes JSON schemas for Gemini's API
├── _generate_with_retry:138 — handles API calls with exponential backoff
├── call_google:168 — primary entry point for interacting with Gemini
└── _token_counts:200 — calculates token usage
```

---

## `backend/agents/versioning` — Version Verification
> Resolves model names and package versions to canonical identifiers

**Files:** `backend/agents/version_hook.py`  `backend/agents/version_oracle.py`
**Deps:** google.genai

```
backend/agents/version_hook.py
├── _extract_tokens:28 — extracts pip, npm, and model version tokens from messages
└── inject_verified_context:46 — verifies tokens and injects a VERIFIED REFERENCES block
```

```
backend/agents/version_oracle.py
├── VerifiedRef:29 — Data model for a verified canonical reference
│   ├── to_dict:39 — Converts reference to dictionary
│   └── unverified:43 — Creates a reference marked as unverified
├── _cache_key:59 — Normalizes input for cache lookup
├── _get_cached:63 — Retrieves reference from cache if not expired
├── _set_cached:70 — Saves reference to cache
├── resolve:96 — Resolves name to canonical form via AI search
├── resolve_many:149 — Resolves multiple names concurrently
└── assert_verified:155 — Validates verification status or raises error
```

---

## `backend/agents/intent-router` — Intent Router
> Zero-shot intent classification for routing requests to hardware or software paths

**Files:** `backend/agents/intent_router.py`
**Deps:** backend/models/client

```
backend/agents/intent_router.py
├── classify:9 — Classifies input text into hardware, software, or mixed intents.
```

---

## `backend/agents/clarifier` — Clarifier Agent
> Generates targeted clarifying questions to refine user intent

**Files:** `backend/agents/clarifier.py`
**Deps:** backend/models/client, backend/memory/rom

```
backend/agents/clarifier.py
└── generate_questions:9 — generates clarifying questions for the given intent
```

---

## `backend/agents/idea-builder` — Idea Builder
> Transforms user intent into an Application Blueprint DAG

**Files:** `backend/agents/idea_builder.py`  `backend/agents/coordinator.py`
**Deps:** backend/models/client, backend/memory/rom, backend/memory/hdd, backend/agents/module-indexer/writer

```
idea_builder.py
├── load_bom:17 — loads hardware bill of materials from JSON
├── _tech_harvester:23 — extracts tech stack and deps from context
├── _rubric_aligner:44 — aligns hardware BOM against intent requirements
├── _risk_assassin:58 — enumerates hardware failure modes and mitigations
├── _emit:76 — helper to send status updates to a callback
└── run:85 — orchestrates worker agents and synthesizes final blueprint
```

```
backend/agents/coordinator.py
├── _now:14 — get current UTC ISO timestamp
├── _run_dynamic_agent:18 — execute single dynamic worker agent task
└── coordinate:38 — orchestrate analysis and spawn additional agents
```

---

## `backend/agents/module-indexer` — Module Indexer
> Scans workspaces to create AST-based symbol trees and module summaries

**Files:** `backend/agents/module_indexer/__init__.py`  `backend/agents/module_indexer/ast_graph.py`  `backend/agents/module_indexer/file_summarizer.py`  `backend/agents/module_indexer/index_writer.py`  `backend/agents/module_indexer/indexer.py`  `backend/agents/module_indexer/module_grouper.py`
**Deps:** backend/models/client, backend/memory/rom

```
backend/agents/module_indexer/__init__.py
├── index_workspace:1 — Indexes the workspace
└── index_files:1 — Indexes specific files
```

```
ast_graph.py
├── Symbol:15 — data model for a discovered code symbol
├── FileGraph:23 — data model for file symbols and imports
├── _checksum:30 — generates a 16-char SHA256 hash of content
├── _parse_python:36 — extracts symbols and imports from Python AST
├── _parse_typescript:83 — extracts symbols and imports from TS/JS via regex
├── _parse_dart:121 — extracts symbols and imports from Dart via regex
├── parse_file:159 — dispatches parsing based on file extension
└── checksum_only:170 — computes file checksum without full parsing
```

```
file_summarizer.py
├── _symbol_hint:24 — generates a formatted list of detected symbols for LLM context
├── summarize_file:34 — orchestrates the parsing and LLM-based summarization of a single file
├── summarize_files:88 — processes multiple files in parallel with bounded concurrency
└── _bounded:94 — internal helper to wrap summarize_file in a semaphore for rate limiting
```

```
index_writer.py
├── _d0mmy_dir:21 — resolve .d0mmy data directory for workspace
├── get_index_json_path:38 — get path to module_index.json
├── get_index_md_path:42 — get path to module_index.md
├── load_index:46 — load index from JSON file
├── write_index:56 — write summaries and modules to JSON and MD
├── _write_md:78 — generate human-readable markdown index
├── get_module_by_id:116 — retrieve module data by ID
├── get_file_entry:124 — retrieve file entry by relative path
└── invalidate_file:129 — remove file entry from index to force re-indexing
```

```
indexer.py
├── _collect_files:27 — scan workspace for supported files
├── _stale_only:40 — filter files that have changed based on checksum
├── index_workspace:57 — orchestrate full workspace scan and indexing
└── index_files:94 — index a specific subset of files
```

```
module_grouper.py
├── _is_internal:21 — Determines if an import is part of the internal project
├── _build_grouper_input:27 — Prepares file summaries and import relations for LLM input
├── group_modules:49 — Orchestrates the module grouping process via LLM or fallback
├── _fill_missing_files:78 — Ensures all files are assigned to at least one module
└── _fallback_groups:99 — Generates a default one-module-per-file mapping
```

---

## `backend/agents/module-indexer/writer` — Index Writer
> Utility for managing the module index JSON and Markdown files

**Files:** `backend/agents/module_indexer/index_writer.py`
**Deps:** backend/config

```
index_writer.py
├── _d0mmy_dir:21 — resolve .d0mmy data directory for workspace
├── get_index_json_path:38 — get path to module_index.json
├── get_index_md_path:42 — get path to module_index.md
├── load_index:46 — load index from JSON file
├── write_index:56 — write summaries and modules to JSON and MD
├── _write_md:78 — generate human-readable markdown index
├── get_module_by_id:116 — retrieve module data by ID
├── get_file_entry:124 — retrieve file entry by relative path
└── invalidate_file:129 — remove file entry from index to force re-indexing
```

---

## `backend/agents/scout` — Scout Agent
> Performs semantic search and technical research for Coder context

**Files:** `backend/agents/scout.py`
**Deps:** backend/memory/hdd, backend/models/client

```
backend/agents/scout.py
├── ScoutReport:26 — data container for scout search results
├── _load_module_index:37 — loads module index from JSON file
├── _score_module:46 — scores module relevance based on keywords
├── _relevant_modules:56 — filters top relevant modules from index
├── _repo_search:66 — retrieves context from ChromaDB and module index
├── _web_search:80 — researches implementation patterns via LLM
└── run:108 — coordinates repo and web search for a sprint
```

---

## `backend/agents/coder` — Coder Agent
> Hierarchical code generation pipeline with complexity scoring and escalation

**Files:** `backend/agents/coder/__init__.py`  `backend/agents/coder/complexity_scorer.py`  `backend/agents/coder/critic.py`  `backend/agents/coder/dispatcher.py`  `backend/agents/coder/gemini_direct.py`  `backend/agents/coder/module_coder.py`  `backend/agents/coder/retriever.py`
**Deps:** backend/agents/scout, backend/models/client, backend/memory/rom

```
backend/agents/coder/__init__.py
└── dispatch_node:1 — Route tasks to appropriate coder nodes
```

```
backend/agents/coder/complexity_scorer.py
├── score:13 — asynchronously scores task complexity (0-10) using a daemon
└── should_escalate:47 — checks if score meets escalation threshold
```

```
critic.py
├── _bom_context:17 — retrieves hardware BOM context for hardware+software mode
└── review:29 — validates proposed code changes against task and BOM
```

```
backend/agents/coder/dispatcher.py
├── dispatch_node:27 — Routes nodes through complexity scoring, generation, and critic review
└── _read_original:124 — Reads and truncates file content for critic review
```

```
gemini_direct.py
├── _build_context:16 — constructs the prompt context for Gemini
└── generate:64 — handles the escalation call to the heavy model
```

```
module_coder.py
├── _build_context:15 — assembles task, research, and file context for the LLM
└── generate:58 — coordinates context building and LLM call to produce code
```

```
retriever.py
├── _load_index:18 — loads module index JSON from disk
├── retrieve_for_modules:27 — returns file contents for given module IDs
└── retrieve_file:74 — reads and truncates a single file
```

---

## `backend/pipelines` — Execution Pipelines
> Orchestrates flow from intent classification to roadmap and execution

**Files:** `backend/pipeline.py`  `backend/exec_pipeline.py`
**Deps:** backend/ws-manager, backend/agents/intent-router, backend/agents/clarifier, backend/agents/idea-builder, backend/agents/coder, backend/agents/module-indexer

```
backend/pipeline.py
├── _now:29 — returns current UTC timestamp
├── _status:33 — creates a status update payload
├── _broadcast:42 — sends status updates to dashboard clients
├── _run_pipeline:46 — orchestrates intent, clarification, and planning
├── _deliver_sprint_graph:147 — delivers final blueprint and sprints to client
├── start:177 — initiates a new planning pipeline task
├── cancel:184 — cancels an active pipeline task
├── inject_interrupt:193 — sends user input to a pending clarification
├── resolve_clarification:199 — resolves clarification future with answers
├── resolve_improve:208 — resolves improvement feedback future
├── restart_with_improve:217 — restarts pipeline with improvement feedback
└── status_relay:114 — relays internal agent status to broadcast
```

```
backend/exec_pipeline.py
├── _sprints_path:17 — gets the path to the sprints.json file
├── _now:33 — returns current UTC timestamp in ISO format
├── _broadcast:37 — sends status updates to dashboard clients
├── _load_sprints:49 — loads sprint data from disk
├── _workspace_root:59 — determines the target workspace directory
├── _run_execution:69 — main loop for scouting and dispatching nodes
├── start_execution:188 — triggers an asynchronous execution task
├── cancel_execution:195 — cancels a running execution task
└── resolve_diff:203 — handles IDE diff acceptance or rejection
```

---

## `backend/apis` — Backend APIs
> FastAPI endpoints for index management, settings, and terminal access

**Files:** `backend/index_api.py`  `backend/settings_api.py`  `backend/terminal.py`
**Deps:** backend/agents/module-indexer, backend/ws-manager, backend/config

```
backend/index_api.py
├── _workspace_root:27 — determines the root directory for indexing
├── get_index:38 — returns the current state of the module index
├── RunIndexRequest:50 — schema for triggering workspace indexing
├── run_index:56 — asynchronously starts the workspace indexing process
│   ├── _run:59 — internal worker for indexing and broadcasting status
│   └── _now:64 — returns current UTC timestamp in ISO format
├── IndexFilesRequest:90 — schema for lazy indexing specific files
├── index_files:96 — indexes a provided list of files
├── get_module:106 — retrieves a specific module entry by ID
└── InvalidateRequest:115 — schema for invalidating a file entry
└── invalidate_file_entry:120 — marks a file for re-indexing
```

```
backend/settings_api.py
├── _read_env:40 — reads and parses .env file into a dictionary
├── _write_env:52 — writes key-value pairs to the .env file
├── _mask:59 — masks sensitive values for display
├── get_settings:66 — API endpoint to retrieve current settings
├── SettingsUpdate:74 — Pydantic model for settings update requests
├── update_settings:82 — API endpoint to update .env settings
├── get_mode:107 — API endpoint to get the project mode
├── ModeUpdate:112 — Pydantic model for mode update requests
├── set_mode:117 — API endpoint to set the project mode
├── get_bom:129 — API endpoint to retrieve the BOM JSON file
├── BomUpdate:138 — Pydantic model for BOM update requests
└── update_bom:143 — API endpoint to update the BOM JSON file
```

```
backend/terminal.py
├── TerminalSession:33 — Manages a single terminal process and its I/O
│   ├── run:39 — Executes a shell command and starts streaming
│   ├── _stream:59 — Reads process output and sends it to the WebSocket
│   ├── write_stdin:79 — Writes input data to the process stdin
│   ├── kill:84 — Terminates the active process and cancels streaming
│   └── running:103 — Checks if the process is currently active
└── terminal_endpoint:110 — WebSocket handler for terminal session interactions
```

---

## `dashboard/core` — Dashboard Core
> Main React application entry and global state/WebSocket management

**Files:** `dashboard/src/App.tsx`  `dashboard/src/main.tsx`  `dashboard/src/ws.ts`  `dashboard/src/types.ts`
**Deps:** @xyflow/react

```
App.tsx
├── Tab:13 — Type for active view selection
├── App:20 — Main dashboard component managing global state
│   ├── onDragStart:131 — Initiates terminal height resizing
│   ├── onMove:135 — Updates terminal height during drag
│   └── onUp:140 — Finalizes terminal height resizing
└── EmptyState:237 — UI fallback for missing data
```

```
dashboard/src/main.tsx
└── render:1: Entry point for the React application
```

```
ws.ts
├── Handler:13 — Type definition for WebSocket message handlers
├── _backoff:22 — Calculates exponential backoff delay for reconnection
├── _emit:26 — Dispatches messages to all registered handlers
├── connect:30 — Initializes WebSocket connection and event listeners
├── send:69 — Sends a message or queues it if disconnected
├── subscribe:77 — Registers a handler for WebSocket messages
├── isConnected:91 — Returns current connection status
└── sessionId:92 — Returns the unique session identifier
```

```
dashboard/src/types.ts
├── NodeKind:1 — Task/milestone node types
├── NodeState:2 — Execution states for nodes
├── AgentRole:3 — Categories of agents (heavy, worker, etc)
├── IntentKind:4 — Hardware/software intent classification
├── BlueprintNode:6 — Structure of a node in the blueprint
├── BlueprintEdge:16 — Connection between two blueprint nodes
├── Sprint:21 — Sprint definition including node IDs and state
├── Blueprint:30 — Full project plan containing nodes, edges, and sprints
├── SprintGraph:39 — Graph representation of a sprint session
├── AgentSpawnEvent:47 — Event data for agent creation
├── WsMessage:55 — WebSocket message envelope for communication
├── ClarificationQuestion:62 — A single clarification request
├── ClarificationState:68 — State tracking for clarification questions
├── ApiCallEvent:73 — Log of an agent's API call
└── VerifiedRef:87 — Reference to a verified canonical resource
```

---

## `dashboard/components` — Dashboard Components
> UI components for sprint graphs, API flows, and settings

**Files:** `dashboard/src/components/ApiFlowPanel.tsx`  `dashboard/src/components/ClarificationPanel.tsx`  `dashboard/src/components/ControlPanel.tsx`  `dashboard/src/components/Header.tsx`  `sprint_graph.tsx`  `dashboard/src/components/SprintGraph.tsx`  `dashboard/src/components/Settings.tsx`  `dashboard/src/components/TerminalPanel.tsx`
**Deps:** @xyflow/react, dagre, @xterm/xterm

```
ApiFlowPanel.tsx
├── Props:16 — Interface for panel input props
├── makeLabel:130 — Generates formatted labels for graph nodes
├── nodeStyle:140 — Returns CSS styles for graph nodes
├── topo:181 — Creates a static structural edge for the topology
├── ApiFlowPanel:192 — Main component for visualizing API flows
├── CallLogItem:433 — Renders a single API call log entry
└── StatCell:462 — Renders a small statistics data cell
```

```
dashboard/src/components/ClarificationPanel.tsx
├── Props:5 — interface for component properties
└── ClarificationPanel:10 — modal panel for answering clarification questions
```

```
dashboard/src/components/ControlPanel.tsx
├── ControlPanel:7 — Main UI component for pipeline control
│   ├── submitIntent:15 — Sends user intent to the pipeline via WebSocket
│   ├── submitInterrupt:21 — Sends an interrupt constraint via WebSocket
│   ├── submitVerify:27 — Verifies a reference via API fetch
│   └── runIndex:38 — Triggers the indexer run via POST request
```

```
dashboard/src/components/Header.tsx
├── Header:12 — Main header component for dashboard status
│   ├── poll:23 — Continuously checks backend launcher status
│   ├── toggleBackend:47 — Starts or stops the backend server
│   └── syncEnv:55 — Triggers environment synchronization
└── Props:3 — Configuration properties for Header component
```

```
SprintGraph.tsx
├── Props:19 — Configuration for the graph component
├── PopupState:28 — State for the sprint detail popup
├── stateClass:37 — Maps node state/kind to CSS classes
├── nodeLabelColor:47 — Maps node state/kind to label colors
├── layoutGraph:57 — Calculates node positions using dagre
├── D0mmyNode:69 — Custom ReactFlow node renderer
├── SprintGraph:108 — Main component for visualizing the sprint graph
│   ├── handler:125 — Closes popup on outside click
│   └── s:193 — Internal helper for handling sprint actions
├── CardProps:291 — Props for individual sprint cards
├── SprintCard:297 — Component rendering sprint details in the popup
├── SprintPopup:331 — Container for the sprint details popup
├── ActionBtn:379 — Generic button for popup actions
├── PopupBtn:389 — Specialized button for popup actions
└── NodeDOMRef:406 — Type for node DOM element references
```

```
Settings.tsx
├── Tab:4 — Tab identifier type
├── ProjectMode:5 — Project mode configuration type
├── Settings:14 — Main settings page component
│   ├── load:28 — Fetches settings, BOM, and project mode
│   ├── switchMode:48 — Updates the project mode (software vs hardware)
│   ├── setField:63 — Updates specific setting field value
│   ├── save:67 — Persists specified setting fields to server
│   ├── saveApiKey:77 — Specifically saves the Google API key
│   ├── saveBom:86 — Validates and saves the Bill of Materials JSON
│   └── flashSaved:105 — Triggers a temporary 'saved' visual state
├── FormField:356 — Renders a labeled input field
├── FieldWithVerify:366 — Renders an input field with a verification action
└── verify:370 — Verifies specific setting value with the server
```

```
dashboard/src/components/TerminalPanel.tsx
├── TerminalPanel:19 — Integrated terminal emulator component
│   ├── connect:87 — Establishes WebSocket connection to backend
│   └── killProcess:131 — Sends kill signal to current running process
└── Props:15 — Component height prop definition
```

---

## `dashboard/config` — Dashboard Config
> Vite configuration for the frontend dashboard

**Files:** `dashboard/vite.config.ts`
**Deps:** @vitejs/plugin-react

```
vite.config.ts
└── defineConfig:4 — configures Vite server, plugins, and proxy routes
```

---

## `vscode/extension` — VS Code Extension
> Manages WebSocket communication and diff views for file changes

**Files:** `vscode-extension/src/extension.ts`  `vscode-extension/src/wsClient.ts`  `vscode-extension/src/diffHandler.ts`
**Deps:** vscode

```
vscode-extension/src/extension.ts
├── activate:9 — Initializes extension, WS client, and commands
├── _scheduleContext:86 — Throttles sending file context updates
├── sendFileContext:91 — Collects and sends active editor and workspace info
└── deactivate:127 — Cleans up WebSocket client on extension shutdown
```

```
vscode-extension/src/wsClient.ts
├── WsClient:6 — WebSocket client for D0mmy backend
│   ├── connect:24 — Establishes connection and sets up listeners
│   ├── on:53 — Registers a handler for a specific message type
│   └── send:59 — Sends a JSON message to the backend
│   └── dispose:74 — Closes connection and cleans up resources
└── MessageHandler:4 — Type definition for message callback functions
```

```
vscode-extension/src/diffHandler.ts
├── PendingDiff:4 — Interface for pending diff state
├── ResultCallback:10 — Callback type for diff results
└── DiffHandler:12 — Manages VS Code diff views and content providers
    │   ├── setResultCallback:18 — Sets the result callback function
    │   ├── provideTextDocumentContent:24 — Provides content for virtual diff documents
    │   ├── showDiff:32 — Opens the VS Code diff editor
    │   ├── accept:59 — Applies the proposed changes to the file
    │   └── reject:88 — Discards the proposed changes
```

---

## `backend/init-files` — Initialization Files
> Python package initialization files

**Files:** `backend/__init__.py`  `backend/agents/__init__.py`  `backend/agents/coder/__init__.py`  `backend/models/__init__.py`  `backend/memory/__init__.py`

```
backend/__init__.py
(empty)
```

```
backend/agents/__init__.py
└── (empty)
```

```
backend/agents/coder/__init__.py
└── dispatch_node:1 — Route tasks to appropriate coder nodes
```

```
backend/models/__init__.py
(empty)
```

```
backend/memory/__init__.py
(empty)
```

---

## `scripts/utils` — Utility Scripts
> Project management, environment setup, and process launching

**Files:** `dev.py`  `scripts/attach.py`  `scripts/launcher.py`  `scripts/projects.py`  `scripts/setup_keys.py`

```
dev.py
├── kill_port_processes:17 — kills processes using a specific port
└── main:39 — orchestrates cleanup, starts launcher and dashboard
```

```
scripts/attach.py
├── _load_env:28 — loads environment variables from a file
├── _write_env:40 — writes environment variables to a file
├── _merge_json:47 — merges updates into a JSON file
└── main:58 — orchestrates the attachment/detachment process
```

```
scripts/launcher.py
├── _is_running:29 — Check if the backend process is currently running
├── _stream_logs:33 — Read and store logs from a subprocess
├── _get_uv_backend_cmd:42 — Determine the command to launch the uvicorn backend
├── Handler:53 — HTTP request handler for backend management
│   ├── log_message:54 — Suppress standard access logs
│   ├── _respond:57 — Helper to send JSON responses with CORS headers
│   ├── do_OPTIONS:66 — Handle CORS preflight requests
│   ├── do_GET:72 — Handle control endpoints (/start, /stop, /restart, /status, /sync, /logs)
│   └── _run_sync:127 — Run 'uv sync' in a background thread
└── main:150 — Entry point to start the HTTP management server
└── _shutdown:157 — Cleanup handler for SIGINT and SIGTERM
```

```
scripts/projects.py
├── _load_registry:51 — loads the project registry from JSON
├── _save_registry:60 — saves the project registry to JSON
├── _load_env:65 — reads key-value pairs from an .env file
├── _write_env:77 — writes key-value pairs to an .env file
├── _merge_vscode_json:84 — updates VS Code settings JSON
├── _next_free_port:95 — finds the next available backend port
├── _pid_alive:103 — checks if a process ID is still running
├── _read_pid:111 — reads a PID from a file
├── cmd_add:122 — registers a new project and configures its env
├── cmd_start:195 — starts the backend for a registered project
├── cmd_stop:264 — stops the backend for a registered project
├── cmd_list:292 — lists all registered projects
├── cmd_remove:308 — removes a project from the registry
├── cmd_open:329 — opens a project's repo in VS Code
└── main:345 — parses CLI arguments and invokes commands
```

```
scripts/setup_keys.py
├── load_existing:67 — reads and parses the existing .env file
├── mask:79 — obfuscates sensitive values for display
├── prompt_field:85 — interactively prompts the user for a field value
├── write_env:118 — writes configured key-value pairs to the .env file
└── main:127 — coordinates the interactive setup process
```

---

## `extension/chrome` — Chrome Extension
> Service worker and content scripts for harvesting content from the browser

**Files:** `extension/background.js`  `extension/content.js`  `extension/popup.js`

```
extension/background.js
├── connect:7 — Establishes WebSocket connection and handles reconnection
├── send:36 — Sends messages to the orchestrator or queues them
├── htmlToMarkdown:79 — Converts HTML strings to basic Markdown format
└── stripTags:102 — Removes all HTML tags from a string
```

```
extension/content.js
└── flashSelection:8 — applies a temporary visual flash to the current text selection
```

```
extension/popup.js
└── checkConnection:3 — checks health endpoint to update UI status
```

---

## `tests/ws` — name
> WebSocket client test script

**Files:** `scratch/test_ws.py`
**Deps:** websockets

```
scratch/test_ws.py
├── test_ws:5 — tests websocket connectivity and basic ping-pong
```

---
