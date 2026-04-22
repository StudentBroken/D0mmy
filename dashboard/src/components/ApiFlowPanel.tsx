import React, { useEffect, useRef, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Node,
  type Edge,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { ApiCallEvent, AgentSpawnEvent, SprintGraph } from '../types'

interface Props {
  calls: ApiCallEvent[]
  graph: SprintGraph | null
  dynAgents: AgentSpawnEvent[]
}

// ─── Role colours ────────────────────────────────────────────────────────────
const ROLE_COLOR: Record<string, string> = {
  daemon: '#aa66ff',
  worker: '#44ddff',
  heavy:  '#ffcc44',
  error:  '#ff4444',
}

const ROLE_LABEL: Record<string, string> = {
  daemon: 'Daemon (Gemma 4 26B MoE)',
  worker: 'Worker (Gemma 4 31B)',
  heavy:  'Heavy (Gemini 3.1 Pro)',
}

// ─── Static topology ─────────────────────────────────────────────────────────
const TOPO_NODES: Node[] = [
  {
    id: 'orchestrator',
    position: { x: 340, y: 20 },
    data: { label: makeLabel('Orchestrator', 'Pipeline Hub', '') },
    style: nodeStyle('#1a4a6a', '#2a6a9a'),
  },
  {
    id: 'intent_router',
    position: { x: 60, y: 140 },
    data: { label: makeLabel('Intent Router', 'Daemon', 'daemon') },
    style: nodeStyle('#1a1a3a', '#4a2a7a'),
  },
  {
    id: 'tech_harvester',
    position: { x: 60, y: 240 },
    data: { label: makeLabel('Tech Harvester', 'Worker', 'worker') },
    style: nodeStyle('#0a2a2a', '#1a5a5a'),
  },
  {
    id: 'rubric_aligner',
    position: { x: 60, y: 330 },
    data: { label: makeLabel('Rubric Aligner', 'Worker', 'worker') },
    style: nodeStyle('#0a2a2a', '#1a5a5a'),
  },
  {
    id: 'risk_assassin',
    position: { x: 60, y: 420 },
    data: { label: makeLabel('Risk Assassin', 'Worker', 'worker') },
    style: nodeStyle('#0a2a2a', '#1a5a5a'),
  },
  {
    id: 'file_summarizer',
    position: { x: 60, y: 510 },
    data: { label: makeLabel('File Summarizer', 'Worker', 'worker') },
    style: nodeStyle('#1a2a1a', '#2a5a2a'),
  },
  {
    id: 'complexity_scorer',
    position: { x: 600, y: 20 },
    data: { label: makeLabel('Complexity Scorer', 'Daemon', 'daemon') },
    style: nodeStyle('#1a1a3a', '#4a2a7a'),
  },
  {
    id: 'module_coder',
    position: { x: 600, y: 110 },
    data: { label: makeLabel('Module Coder', 'Worker', 'worker') },
    style: nodeStyle('#0a2a2a', '#1a5a5a'),
  },
  {
    id: 'gemini_direct',
    position: { x: 600, y: 200 },
    data: { label: makeLabel('Direct Coder', 'Heavy', 'heavy') },
    style: nodeStyle('#2a1a0a', '#5a3a0a'),
  },
  {
    id: 'code_critic',
    position: { x: 600, y: 290 },
    data: { label: makeLabel('Code Critic', 'Heavy', 'heavy') },
    style: nodeStyle('#2a1a0a', '#5a3a0a', 160),
  },
  {
    id: 'time_estimator',
    position: { x: 600, y: 400 },
    data: { label: makeLabel('Time Estimator', 'Worker', 'worker') },
    style: nodeStyle('#0a2a2a', '#1a5a5a'),
  },
  {
    id: 'intersection_architect',
    position: { x: 600, y: 490 },
    data: { label: makeLabel('Intersect. Arch.', 'Worker', 'worker') },
    style: nodeStyle('#0a2a2a', '#1a5a5a'),
  },
  {
    id: 'google_api',
    position: { x: 860, y: 240 },
    data: { label: makeLabel('Google AI API', '⚡ External', '') },
    style: nodeStyle('#1a2a0a', '#2a4a0a', 180),
  },
  {
    id: 'chromadb',
    position: { x: 340, y: 380 },
    data: { label: makeLabel('ChromaDB', '🗄 HDD Memory', '') },
    style: nodeStyle('#0a1a2a', '#1a3a4a'),
  },
  {
    id: 'blueprint_synthesizer',
    position: { x: 340, y: 200 },
    data: { label: makeLabel('Blueprint Synth', 'Heavy', 'heavy') },
    style: nodeStyle('#2a1a0a', '#5a3a0a'),
  },
]

function makeLabel(name: string, sub: string, role: string) {
  const color = ROLE_COLOR[role] || '#7a9aaa'
  return (
    <div style={{ fontSize: 11, lineHeight: 1.4, textAlign: 'center' }}>
      <div style={{ fontWeight: 700, marginBottom: 1 }}>{name}</div>
      <div style={{ opacity: 0.65, fontSize: 10, color }}>{sub}</div>
    </div>
  )
}

function nodeStyle(bg: string, border: string, w = 160): React.CSSProperties {
  return {
    background: bg,
    border: `1px solid ${border}`,
    borderRadius: 8,
    color: 'var(--text-2)',
    width: w,
    padding: '8px 10px',
    textAlign: 'center' as const,
  }
}

// Static structural edges (dim)
const TOPO_EDGES: Edge[] = [
  topo('orchestrator', 'intent_router'),
  topo('orchestrator', 'tech_harvester'),
  topo('orchestrator', 'rubric_aligner'),
  topo('orchestrator', 'risk_assassin'),
  topo('orchestrator', 'file_summarizer'),
  topo('orchestrator', 'complexity_scorer'),
  topo('orchestrator', 'module_coder'),
  topo('orchestrator', 'gemini_direct'),
  topo('orchestrator', 'code_critic'),
  topo('orchestrator', 'blueprint_synthesizer'),
  topo('orchestrator', 'time_estimator'),
  topo('orchestrator', 'intersection_architect'),
  topo('orchestrator', 'chromadb'),
  topo('intent_router', 'google_api'),
  topo('tech_harvester', 'google_api'),
  topo('rubric_aligner', 'google_api'),
  topo('risk_assassin', 'google_api'),
  topo('file_summarizer', 'google_api'),
  topo('complexity_scorer', 'google_api'),
  topo('module_coder', 'google_api'),
  topo('gemini_direct', 'google_api'),
  topo('code_critic', 'google_api'),
  topo('blueprint_synthesizer', 'google_api'),
  topo('time_estimator', 'google_api'),
  topo('intersection_architect', 'google_api'),
]

function topo(from: string, to: string): Edge {
  return {
    id: `topo_${from}_${to}`,
    source: from,
    target: to,
    style: { stroke: '#1a3a4a', strokeWidth: 1, opacity: 0.4 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#1a3a4a' },
  }
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function ApiFlowPanel({ calls, graph, dynAgents }: Props) {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(TOPO_NODES)
  const [rfEdges, setEdges, onEdgesChange] = useEdgesState(TOPO_EDGES)
  const logRef = useRef<HTMLDivElement>(null)

  // Rebuild live call edges whenever calls change
  useEffect(() => {
    const liveEdges: Edge[] = []

    for (const c of calls) {
      const agentNode = rfNodes.find(n => n.id === c.agent)
      if (!agentNode) continue

      const color = c.status === 'error' ? ROLE_COLOR.error : (ROLE_COLOR[c.role] || '#aaaaaa')
      const isActive = c.status === 'start'
      const opacity = c.status === 'complete' ? 0.5 : 1

      const isChroma = c.agent === 'chromadb'
      liveEdges.push({
        id: `call_${c.call_id}`,
        source: c.agent,
        target: isChroma ? 'orchestrator' : 'google_api',
        animated: isActive,
        style: {
          stroke: color,
          strokeWidth: isActive ? 2.5 : 1.5,
          opacity,
          filter: isActive ? `drop-shadow(0 0 4px ${color})` : undefined,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color },
        label: isActive ? c.goal : (c.duration_ms ? `${c.duration_ms}ms` : undefined),
        labelStyle: { fontSize: 9, fill: color, fontWeight: 600 },
        labelBgStyle: { fill: '#0a0f18', fillOpacity: 0.85 },
      })
    }

    // Static edges for dynamic agents (parent → agent, agent → google_api)
    const dynEdges: Edge[] = dynAgents.flatMap(a => [
      {
        id: `dyn_in_${a.agent_id}`,
        source: a.parent,
        target: a.agent_id,
        style: { stroke: '#2a6a4a', strokeWidth: 1, strokeDasharray: '4 3' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#2a6a4a' },
      },
      {
        id: `dyn_out_${a.agent_id}`,
        source: a.agent_id,
        target: 'google_api',
        style: { stroke: '#1a5a3a', strokeWidth: 1, strokeDasharray: '4 3' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#1a5a3a' },
      },
    ])

    setEdges([...TOPO_EDGES, ...dynEdges, ...liveEdges])
  }, [calls, rfNodes, dynAgents, setEdges])

  // Add dynamic agent nodes when agents are spawned
  useEffect(() => {
    if (!dynAgents.length) {
      setRfNodes(TOPO_NODES)
      return
    }
    const extra: Node[] = dynAgents.map((a, i) => ({
      id: a.agent_id,
      position: { x: 340, y: 560 + i * 90 },
      data: {
        label: makeLabel(
          a.agent_id.replace('dynamic_', ''),
          `⚡ ${a.goal.slice(0, 36)}…`,
          'worker',
        ),
      },
      style: {
        ...nodeStyle('#0a2a1a', '#1a5a2a'),
        border: '1px dashed #2a7a4a',
      },
    }))
    setRfNodes([...TOPO_NODES, ...extra])
  }, [dynAgents, setRfNodes])

  // Auto-scroll log to bottom
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [calls])

  const handleExport = useCallback(() => {
    if (!graph) return
    const blob = new Blob([JSON.stringify(graph.blueprint, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `blueprint_${graph.blueprint.project_name?.replace(/\s+/g, '_') || 'export'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [graph])

  const activeCount = calls.filter(c => c.status === 'start').length
  const totalTokens = calls.reduce((s, c) => s + (c.token_in || 0) + (c.token_out || 0), 0)

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Graph canvas ── */}
      <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          nodesDraggable
          nodesConnectable={false}
        >
          <Background variant={BackgroundVariant.Dots} color="var(--border)" />
          <Controls style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }} />
        </ReactFlow>

        {/* Status bar */}
        <div style={{ position: 'absolute', top: 10, left: 10, display: 'flex', gap: 8, alignItems: 'center', zIndex: 5 }}>
          {activeCount > 0 && (
            <div style={{
              background: 'var(--bg-panel)', border: '1px solid var(--purple)',
              borderRadius: 99, padding: '4px 12px', fontSize: 11, color: 'var(--purple)',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span className="dot dot-pulse" style={{ background: 'var(--purple)', boxShadow: '0 0 5px var(--purple)' }} />
              {activeCount} active
            </div>
          )}
          {totalTokens > 0 && (
            <div style={{
              background: 'var(--bg-panel)', border: '1px solid var(--border)',
              borderRadius: 99, padding: '4px 12px', fontSize: 11, color: 'var(--text-muted)',
            }}>
              {totalTokens.toLocaleString()} tokens
            </div>
          )}
        </div>

        {/* Legend */}
        <div style={{
          position: 'absolute', bottom: 10, left: 10, zIndex: 5,
          background: 'var(--bg-panel)', border: '1px solid var(--border)',
          borderRadius: 'var(--r-lg)', padding: '7px 12px',
          display: 'flex', gap: 14, alignItems: 'center',
        }}>
          <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 700 }}>Model</span>
          {Object.entries(ROLE_LABEL).map(([role, label]) => (
            <div key={role} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 20, height: 2, background: ROLE_COLOR[role], boxShadow: `0 0 4px ${ROLE_COLOR[role]}` }} />
              <span style={{ fontSize: 9, color: 'var(--text-2)' }}>{label}</span>
            </div>
          ))}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 20, height: 2, background: ROLE_COLOR.error }} />
            <span style={{ fontSize: 9, color: 'var(--text-2)' }}>Error</span>
          </div>
        </div>
      </div>

      {/* ── Right panel: log + export ── */}
      <div style={{
        width: 280, flexShrink: 0,
        display: 'flex', flexDirection: 'column',
        background: 'var(--bg-panel)', borderLeft: '1px solid var(--border)',
      }}>

        {/* Header */}
        <div style={{
          padding: '10px 14px', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>API Call Log</span>
          <button
            className="btn-ghost"
            onClick={handleExport}
            disabled={!graph}
            style={{
              fontSize: 10, padding: '3px 9px',
              color: graph ? 'var(--green)' : undefined,
              borderColor: graph ? '#1a4432' : undefined,
              opacity: graph ? 1 : .4,
            }}
          >
            ↓ Export
          </button>
        </div>

        {/* Call log */}
        <div
          ref={logRef}
          style={{
            flex: 1, overflowY: 'auto', padding: '6px 0',
            display: 'flex', flexDirection: 'column', gap: 1,
          }}
        >
          {calls.length === 0 && (
            <div style={{
              padding: '40px 14px', textAlign: 'center',
              fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.7,
            }}>
              No API calls yet.<br />Start a pipeline to see live traffic.
            </div>
          )}

          {[...calls].reverse().map((c) => (
            <CallLogItem key={`${c.call_id}_${c.status}`} call={c} />
          ))}
        </div>

        {/* Stats footer */}
        {calls.length > 0 && (
          <div style={{ borderTop: '1px solid var(--border)', padding: '8px 12px' }}>
            <div className="stats-grid">
              <StatCell label="Calls"      value={calls.filter(c => c.status !== 'start').length} />
              <StatCell label="Active"     value={activeCount} hi={activeCount > 0} />
              <StatCell label="Tokens in"  value={calls.reduce((s, c) => s + (c.token_in || 0), 0)} />
              <StatCell label="Tokens out" value={calls.reduce((s, c) => s + (c.token_out || 0), 0)} />
              <StatCell label="Avg latency" value={(() => {
                const done = calls.filter(c => c.duration_ms)
                if (!done.length) return '—'
                return `${(done.reduce((s, c) => s + (c.duration_ms || 0), 0) / done.length / 1000).toFixed(1)}s`
              })()} />
              <StatCell label="Errors" value={calls.filter(c => c.status === 'error').length}
                hi={calls.some(c => c.status === 'error')} err={calls.some(c => c.status === 'error')} />
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.3 } }
      `}</style>
    </div>
  )
}

function CallLogItem({ call: c }: { call: ApiCallEvent }) {
  const color = c.status === 'error' ? ROLE_COLOR.error : (ROLE_COLOR[c.role] || 'var(--text-muted)')
  const statusIcon = c.status === 'start' ? '⟳' : c.status === 'complete' ? '✓' : '✗'
  const time = new Date(c.timestamp).toLocaleTimeString([], { hour12: false })

  return (
    <div style={{
      padding: '5px 12px', borderLeft: `2px solid ${color}`,
      marginLeft: 6, opacity: c.status === 'complete' ? 0.7 : 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
        <span style={{ color, fontSize: 11 }}>{statusIcon}</span>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text)' }}>{c.agent}</span>
        <span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>{time}</span>
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-2)', lineHeight: 1.4 }}>{c.goal}</div>
      {c.status !== 'start' && (
        <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
          {c.duration_ms != null && <span style={{ fontSize: 9, color: 'var(--green)', fontFamily: 'var(--mono)' }}>{c.duration_ms}ms</span>}
          {(c.token_in || c.token_out)
            ? <span style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>{c.token_in ?? 0}↑ {c.token_out ?? 0}↓</span>
            : null}
          {c.error && <span style={{ fontSize: 9, color: 'var(--red)' }} title={c.error}>{c.error.slice(0, 40)}…</span>}
        </div>
      )}
    </div>
  )
}

function StatCell({ label, value, hi, err }: { label: string; value: number | string; hi?: boolean; err?: boolean }) {
  return (
    <div className="stat-cell">
      <div className="stat-cell__label">{label}</div>
      <div className={`stat-cell__value${hi && !err ? ' stat-cell__value--hi' : err && hi ? ' stat-cell__value--err' : ''}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  )
}
