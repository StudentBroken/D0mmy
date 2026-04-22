export type NodeKind = 'task' | 'hard_stop' | 'milestone' | 'interrupted'
export type NodeState = 'idle' | 'running' | 'complete' | 'blocked' | 'interrupted'
export type AgentRole = 'heavy' | 'worker' | 'daemon' | 'human'
export type IntentKind = 'hardware' | 'software' | 'mixed'

export interface BlueprintNode {
  id: string
  label: string
  type: NodeKind
  estimated_hours: number
  depends_on?: string[]
  agent?: AgentRole
  state?: NodeState
}

export interface BlueprintEdge {
  from: string
  to: string
}

export interface Sprint {
  sprint_id: number
  title: string
  node_ids: string[]
  estimated_hours: number
  hard_stop: boolean
  state?: NodeState
}

export interface Blueprint {
  project_name: string
  intent: string
  hardware_constraints: string[]
  nodes: BlueprintNode[]
  edges: BlueprintEdge[]
  sprints: Sprint[]
}

export interface SprintGraph {
  session_id: string
  blueprint: Blueprint
  sprints: Sprint[]
  intent: string
  intent_kind: IntentKind
}

export interface AgentSpawnEvent {
  agent_id: string
  goal: string
  parent: string
  role: string
  model: string
}

export interface WsMessage {
  type: 'status_update' | 'sprint_graph' | 'code_diff' | 'error' | 'ack' | 'interrupt' | 'ping' | 'pong' | 'api_call' | 'clarification_needed' | 'agent_spawned'
  payload: Record<string, unknown>
  session_id: string
  timestamp: string
}

export interface ClarificationQuestion {
  id: string
  question: string
  hint: string
}

export interface ClarificationState {
  session_id: string
  questions: ClarificationQuestion[]
}

export interface ApiCallEvent {
  call_id: string
  agent: string
  role: 'heavy' | 'worker' | 'daemon'
  model: string
  goal: string
  status: 'start' | 'complete' | 'error'
  duration_ms?: number
  token_in?: number
  token_out?: number
  error?: string
  timestamp: string
}

export interface VerifiedRef {
  input_name: string
  canonical: string
  version: string
  kind: string
  verified: boolean
  source: string
  notes: string
  verified_at: number
}
