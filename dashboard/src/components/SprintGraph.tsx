import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  BackgroundVariant,
  type NodeProps,
} from '@xyflow/react'
import dagre from 'dagre'
import '@xyflow/react/dist/style.css'
import { send, sessionId } from '../ws'
import type { Blueprint, BlueprintNode, Sprint } from '../types'

interface Props {
  blueprint: Blueprint
  sprints: Sprint[]
  onApprove: (sprintId: number) => void
  activeStates: Record<string, string>
  intent: string
  onRedo: () => void
}

interface PopupState { nodeId: string; sprint: Sprint | null; x: number; y: number }

const NODE_W = 188
const NODE_H = 62

const AGENT_COLOR: Record<string, string> = {
  heavy: 'var(--amber)', worker: 'var(--cyan)', daemon: 'var(--purple)',
}

function stateClass(kind: string, state: string): string {
  if (state === 'running')     return 'rf-node--running'
  if (state === 'complete')    return 'rf-node--complete'
  if (state === 'blocked')     return 'rf-node--blocked'
  if (state === 'interrupted') return 'rf-node--interrupted'
  if (kind === 'hard_stop')    return 'rf-node--hard_stop'
  if (kind === 'milestone')    return 'rf-node--milestone'
  return 'rf-node--idle'
}

function nodeLabelColor(state: string, kind: string): string {
  if (state === 'running')     return 'var(--blue)'
  if (state === 'complete')    return 'var(--green)'
  if (state === 'blocked')     return 'var(--red)'
  if (state === 'interrupted') return 'var(--orange)'
  if (kind === 'hard_stop')    return 'var(--red)'
  if (kind === 'milestone')    return 'var(--green)'
  return 'var(--text)'
}

function layoutGraph(nodes: BlueprintNode[], edges: { from: string; to: string }[]) {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 56 })
  g.setDefaultEdgeLabel(() => ({}))
  nodes.forEach(n => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  edges.forEach(e => g.setEdge(e.from, e.to))
  dagre.layout(g)
  return g
}

/* ── Custom ReactFlow node ──────────────────────────────────────────────── */

function D0mmyNode({ data }: NodeProps) {
  const d = data as {
    label: string; kind: string; state: string
    hours: number; agent?: string; sprintId?: number; hasSprint: boolean
  }
  const agentColor = AGENT_COLOR[d.agent ?? ''] ?? 'var(--text-muted)'
  const labelColor = nodeLabelColor(d.state, d.kind)

  return (
    <div className={`rf-node ${stateClass(d.kind, d.state)}`}
      style={{ width: NODE_W, minHeight: NODE_H, cursor: d.hasSprint ? 'pointer' : 'default' }}>
      <div className="rf-node__label" style={{ color: labelColor }}>{d.label}</div>
      <div className="rf-node__meta">
        {d.hours > 0 && (
          <span className="rf-node__tag" style={{ color: 'var(--text-muted)', border: '1px solid var(--border)', background: 'var(--bg)' }}>
            {d.hours}h
          </span>
        )}
        {d.agent && (
          <span className="rf-node__tag" style={{ color: agentColor }}>{d.agent}</span>
        )}
        {d.kind === 'hard_stop' && (
          <span className="rf-node__tag" style={{ color: 'var(--red)', background: 'var(--red-dim)', border: '1px solid #4a1a24' }}>STOP</span>
        )}
        {d.kind === 'milestone' && (
          <span className="rf-node__tag" style={{ color: 'var(--green)', background: 'var(--green-dim)', border: '1px solid #1e5a38' }}>◆</span>
        )}
        {d.sprintId !== undefined && (
          <span style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginLeft: 'auto' }}>S{d.sprintId}</span>
        )}
      </div>
    </div>
  )
}

const NODE_TYPES = { custom: D0mmyNode }

/* ── Main component ─────────────────────────────────────────────────────── */

export default function SprintGraph({ blueprint, sprints, onApprove, activeStates, intent, onRedo }: Props) {
  const [rfNodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [rfEdges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [sidebarOpen, setSidebarOpen]      = useState(true)
  const [popup, setPopup]                  = useState<PopupState | null>(null)
  const [improveOpen, setImproveOpen]      = useState<Record<number, boolean>>({})
  const [improveFeedback, setImproveFeedback] = useState<Record<number, string>>({})
  const popupRef = useRef<HTMLDivElement>(null)

  const sprintByNode = useMemo(() => {
    const m: Record<string, Sprint> = {}
    sprints.forEach(s => s.node_ids.forEach(id => { m[id] = s }))
    return m
  }, [sprints])

  useEffect(() => {
    if (!popup) return
    function handler(e: MouseEvent) {
      if (popupRef.current && !popupRef.current.contains(e.target as NodeDOMRef)) setPopup(null)
    }
    window.addEventListener('mousedown', handler)
    return () => window.removeEventListener('mousedown', handler)
  }, [popup])

  const handleNodeClick = useCallback((ev: React.MouseEvent, node: Node) => {
    const sprint = sprintByNode[node.id] ?? null
    setPopup({
      nodeId: node.id, sprint,
      x: Math.min(ev.clientX + 8, window.innerWidth - 300),
      y: Math.min(ev.clientY - 10, window.innerHeight - 280),
    })
  }, [sprintByNode])

  const handleDecline = useCallback((sprintId: number) => {
    send({ type: 'sprint_declined', payload: { sprint_id: sprintId }, session_id: sessionId(), timestamp: new Date().toISOString() })
    setPopup(null)
  }, [])

  const handleApproveAndClose = useCallback((sprintId: number) => {
    onApprove(sprintId); setPopup(null)
  }, [onApprove])

  const handleImproveSubmit = useCallback((sprintId: number) => {
    const fb = improveFeedback[sprintId] ?? ''
    if (!fb.trim()) return
    send({ type: 'sprint_improve', payload: { sprint_id: sprintId, feedback: fb, intent }, session_id: sessionId(), timestamp: new Date().toISOString() })
    setImproveOpen(p => ({ ...p, [sprintId]: false }))
    setImproveFeedback(p => ({ ...p, [sprintId]: '' }))
    setPopup(null)
  }, [improveFeedback, intent])

  useEffect(() => {
    const g = layoutGraph(blueprint.nodes, blueprint.edges)
    const nodes: Node[] = blueprint.nodes.map(n => {
      const pos   = g.node(n.id)
      const state = activeStates[n.id] ?? 'idle'
      const sprint = sprintByNode[n.id]
      return {
        id: n.id, type: 'custom',
        position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
        data: { label: n.label, kind: n.type, state, hours: n.estimated_hours, agent: n.agent, sprintId: sprint?.sprint_id, hasSprint: Boolean(sprint) },
      }
    })
    const edges: Edge[] = blueprint.edges.map((e, i) => ({
      id: `e${i}`, source: e.from, target: e.to,
      animated: activeStates[e.from] === 'running',
      style: { stroke: activeStates[e.from] === 'running' ? 'var(--blue)' : 'var(--border-hi)', strokeWidth: 1.5, opacity: .7 },
    }))
    setNodes(nodes); setEdges(edges)
  }, [blueprint, activeStates, sprintByNode, setNodes, setEdges])

  const totalHours = sprints.reduce((a, s) => a + s.estimated_hours, 0)

  return (
    <div style={{ height: '100%', width: '100%', display: 'flex', position: 'relative' }}>

      {/* Canvas */}
      <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
        <ReactFlow nodes={rfNodes} edges={rfEdges} nodeTypes={NODE_TYPES}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick} fitView fitViewOptions={{ padding: 0.22 }}>
          <Background variant={BackgroundVariant.Dots} color="var(--border)" gap={22} size={1} />
          <Controls style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }} />
          <MiniMap style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)' }}
            nodeColor={n => {
              const s = (n.data as { state: string }).state ?? 'idle'
              return s === 'running' ? '#0d1e42' : s === 'complete' ? '#091e17' : s === 'blocked' ? '#280c12' : '#0e1020'
            }} />
        </ReactFlow>

        {/* Stats pill */}
        <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 5 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '5px 12px', background: 'var(--bg-panel)',
            border: '1px solid var(--border)', borderRadius: 99, fontSize: 11,
          }}>
            <span style={{ color: 'var(--text-2)', fontWeight: 600 }}>{sprints.length}</span>
            <span style={{ color: 'var(--text-muted)' }}>sprints</span>
            <span style={{ color: 'var(--border-hi)' }}>·</span>
            <span style={{ color: 'var(--text-2)', fontWeight: 600 }}>{totalHours.toFixed(1)}h</span>
          </div>
        </div>

        {/* Sidebar toggle tab */}
        <button onClick={() => setSidebarOpen(o => !o)} style={{
          position: 'absolute', top: '50%', right: 0, transform: 'translateY(-50%)',
          background: 'var(--bg-raised)', border: '1px solid var(--border-hi)',
          borderRight: 'none', borderRadius: '8px 0 0 8px',
          color: 'var(--text-muted)', fontSize: 9, padding: '12px 5px',
          cursor: 'pointer', writingMode: 'vertical-rl',
          letterSpacing: '.08em', textTransform: 'uppercase',
          zIndex: 5, fontFamily: 'var(--sans)', fontWeight: 700,
        }}>
          {sidebarOpen ? '› Sprints' : '‹ Sprints'}
        </button>
      </div>

      {/* Sprint sidebar */}
      {sidebarOpen && (
        <div style={{
          width: 258, flexShrink: 0,
          background: 'var(--bg-panel)', borderLeft: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 12px', borderBottom: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'var(--bg-raised)', flexShrink: 0,
          }}>
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Sprints <span style={{ color: 'var(--text-2)', fontWeight: 400, letterSpacing: 0 }}>{sprints.length}</span>
            </span>
            <button className="btn-ghost" onClick={onRedo} style={{ fontSize: 10, padding: '3px 9px' }}>↺ Redo</button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 7 }}>
            {sprints.map(s => (
              <SprintCard key={s.sprint_id} sprint={s}
                improveOpen={improveOpen[s.sprint_id] ?? false}
                feedback={improveFeedback[s.sprint_id] ?? ''}
                onApprove={() => handleApproveAndClose(s.sprint_id)}
                onDecline={() => handleDecline(s.sprint_id)}
                onToggleImprove={() => setImproveOpen(p => ({ ...p, [s.sprint_id]: !p[s.sprint_id] }))}
                onFeedbackChange={v => setImproveFeedback(p => ({ ...p, [s.sprint_id]: v }))}
                onImproveSubmit={() => handleImproveSubmit(s.sprint_id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Node popup */}
      {popup && (
        <div ref={popupRef} className="fade-in" style={{
          position: 'fixed', left: popup.x, top: popup.y, zIndex: 1000, width: 282,
          background: 'var(--bg-raised)', border: '1px solid var(--border-hi)',
          borderRadius: 'var(--r-xl)', boxShadow: '0 20px 64px rgba(0,0,0,.85)', overflow: 'hidden',
        }} onClick={e => e.stopPropagation()}>
          {popup.sprint ? (
            <SprintPopup sprint={popup.sprint} nodeId={popup.nodeId}
              onApprove={() => handleApproveAndClose(popup.sprint!.sprint_id)}
              onDecline={() => handleDecline(popup.sprint!.sprint_id)}
              onClose={() => setPopup(null)}
              onImproveSubmit={fb => {
                send({ type: 'sprint_improve', payload: { sprint_id: popup.sprint!.sprint_id, feedback: fb, intent }, session_id: sessionId(), timestamp: new Date().toISOString() })
                setPopup(null)
              }} />
          ) : (
            <div style={{ padding: 16 }}>
              <div className="sec-label">Unassigned Node</div>
              <div style={{ fontSize: 12, color: 'var(--text)', fontFamily: 'var(--mono)', marginBottom: 4 }}>{popup.nodeId}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>Not assigned to any sprint.</div>
              <button className="btn-ghost" onClick={() => setPopup(null)} style={{ fontSize: 11 }}>✕ Close</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Sprint card ──────────────────────────────────────────────────────────── */

interface CardProps {
  sprint: Sprint; improveOpen: boolean; feedback: string
  onApprove: () => void; onDecline: () => void; onToggleImprove: () => void
  onFeedbackChange: (v: string) => void; onImproveSubmit: () => void
}

function SprintCard({ sprint: s, improveOpen, feedback, onApprove, onDecline, onToggleImprove, onFeedbackChange, onImproveSubmit }: CardProps) {
  return (
    <div className="sprint-card" style={{ marginBottom: 6 }}>
      <div style={{ padding: '9px 11px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
          <span style={{ fontWeight: 700, fontSize: 11, color: s.hard_stop ? 'var(--red)' : 'var(--blue)', fontFamily: 'var(--mono)' }}>S{s.sprint_id}</span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{s.estimated_hours}h</span>
          {s.hard_stop && <span className="badge badge-red" style={{ fontSize: 9, padding: '0 5px' }}>STOP</span>}
          <span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--text-muted)' }}>{s.node_ids.length} nodes</span>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-2)', lineHeight: 1.45, marginBottom: 8 }}>{s.title}</div>
        <div style={{ display: 'flex', gap: 4, marginBottom: 9 }}>
          <ActionBtn color="var(--green)" bg="var(--green-dim)" border="#1a4432" onClick={onApprove}>▶ Approve</ActionBtn>
          <ActionBtn color="var(--amber)" bg="var(--amber-dim)" border="#3a2a10" onClick={onToggleImprove} active={improveOpen}>✎</ActionBtn>
          <ActionBtn color="var(--red)" bg="var(--red-dim)" border="#3a1422" onClick={onDecline}>✕</ActionBtn>
        </div>
      </div>
      {improveOpen && (
        <div style={{ padding: '8px 11px 10px', borderTop: '1px solid var(--border)' }}>
          <textarea autoFocus value={feedback} onChange={e => onFeedbackChange(e.target.value)}
            placeholder="What needs to change? (⌘↵ to send)" rows={2}
            style={{ fontSize: 11, resize: 'none', marginBottom: 5, minHeight: 0 }}
            onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onImproveSubmit() }} />
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <ActionBtn color="var(--amber)" bg="var(--amber-dim)" border="#3a2a10" onClick={onImproveSubmit} disabled={!feedback.trim()}>Send ▶</ActionBtn>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Sprint popup ─────────────────────────────────────────────────────────── */

function SprintPopup({ sprint, nodeId, onApprove, onDecline, onClose, onImproveSubmit }: {
  sprint: Sprint; nodeId: string
  onApprove: () => void; onDecline: () => void; onClose: () => void
  onImproveSubmit: (fb: string) => void
}) {
  const [showImprove, setShowImprove] = useState(false)
  const [feedback, setFeedback]       = useState('')
  return (
    <>
      <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-raised)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 700, fontSize: 12, fontFamily: 'var(--mono)', color: sprint.hard_stop ? 'var(--red)' : 'var(--blue)' }}>Sprint {sprint.sprint_id}</span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{sprint.estimated_hours}h</span>
          {sprint.hard_stop && <span className="badge badge-red" style={{ fontSize: 9 }}>HARD STOP</span>}
        </div>
        <button className="btn-ghost" onClick={onClose} style={{ fontSize: 10, padding: '2px 7px' }}>✕</button>
      </div>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.5 }}>{sprint.title}</div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--mono)' }}>{nodeId}</div>
      </div>
      {!showImprove ? (
        <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 5 }}>
          <PopupBtn color="var(--green)" bg="var(--green-dim)" border="#1a4432" onClick={onApprove}>▶ Approve Sprint</PopupBtn>
          <PopupBtn color="var(--amber)" bg="var(--amber-dim)" border="#3a2a10" onClick={() => setShowImprove(true)}>✎ Request Improvements</PopupBtn>
          <PopupBtn color="var(--red)" bg="var(--red-dim)" border="#3a1422" onClick={onDecline}>✕ Decline &amp; Stop</PopupBtn>
        </div>
      ) : (
        <div style={{ padding: '10px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-2)', marginBottom: 7 }}>What needs to change?</div>
          <textarea autoFocus value={feedback} onChange={e => setFeedback(e.target.value)}
            rows={3} placeholder="Describe changes… (⌘↵ to send)"
            style={{ fontSize: 11, resize: 'none', marginBottom: 8, minHeight: 0 }}
            onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && feedback.trim()) onImproveSubmit(feedback) }} />
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn-ghost" onClick={() => setShowImprove(false)} style={{ fontSize: 11 }}>← Back</button>
            <PopupBtn color="var(--amber)" bg="var(--amber-dim)" border="#3a2a10"
              onClick={() => feedback.trim() && onImproveSubmit(feedback)}
              style={{ flex: 1, opacity: feedback.trim() ? 1 : .4 }}>Send ▶</PopupBtn>
          </div>
        </div>
      )}
    </>
  )
}

/* ── Micro helpers ────────────────────────────────────────────────────────── */

function ActionBtn({ color, bg, border, onClick, active: _active, disabled, children }: {
  color: string; bg: string; border: string; onClick: () => void
  active?: boolean; disabled?: boolean; children: React.ReactNode
}) {
  return (
    <button className="action-btn" onClick={onClick} disabled={disabled}
      style={{ background: bg, borderColor: border, color }}>{children}</button>
  )
}

function PopupBtn({ color, bg, border, onClick, children, style }: {
  color: string; bg: string; border: string; onClick: () => void
  children: React.ReactNode; style?: React.CSSProperties
}) {
  return (
    <button onClick={onClick} style={{
      background: bg, border: `1px solid ${border}`, borderRadius: 'var(--r)',
      color, fontSize: 12, padding: '8px 12px', cursor: 'pointer',
      width: '100%', textAlign: 'left', fontFamily: 'var(--sans)', fontWeight: 500,
      transition: 'filter .12s', ...style,
    }}
      onMouseEnter={e => (e.currentTarget.style.filter = 'brightness(1.15)')}
      onMouseLeave={e => (e.currentTarget.style.filter = '')}
    >{children}</button>
  )
}

type NodeDOMRef = globalThis.Node
