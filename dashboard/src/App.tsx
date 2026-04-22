import { useState, useEffect, useCallback, useRef } from 'react'
import { ReactFlowProvider } from '@xyflow/react'
import { subscribe, send, isConnected, sessionId } from './ws'
import type { WsMessage, SprintGraph, Sprint, ApiCallEvent, ClarificationState, AgentSpawnEvent } from './types'
import SprintGraph_ from './components/SprintGraph'
import ApiFlowPanel from './components/ApiFlowPanel'
import ClarificationPanel from './components/ClarificationPanel'
import ControlPanel from './components/ControlPanel'
import Settings from './components/Settings'
import Header from './components/Header'
import TerminalPanel from './components/TerminalPanel'

type Tab = 'graph' | 'apiflow'

const MAX_CALLS        = 200
const TERMINAL_DEFAULT = 260
const TERMINAL_MIN     = 120
const TERMINAL_MAX     = 600

export default function App() {
  const [connected,    setConnected]    = useState(isConnected())
  const [status,       setStatus]       = useState('Waiting for backend…')
  const [graph,        setGraph]        = useState<SprintGraph | null>(null)
  const [activeStates, setActiveStates] = useState<Record<string, string>>({})
  const [terminalOpen, setTerminalOpen] = useState(true)
  const [terminalH,    setTerminalH]    = useState(TERMINAL_DEFAULT)
  const [activeTab,    setActiveTab]    = useState<Tab>('graph')
  const [apiCalls,     setApiCalls]     = useState<ApiCallEvent[]>([])
  const [clarification,setClarification]= useState<ClarificationState | null>(null)
  const [dynAgents,    setDynAgents]    = useState<AgentSpawnEvent[]>([])
  const [indexing,     setIndexing]     = useState(false)

  const callsRef  = useRef<Map<string, ApiCallEvent>>(new Map())
  const dragging  = useRef(false)
  const dragStart = useRef({ y: 0, h: 0 })

  const inFlightCount = apiCalls.filter(c => c.status === 'start').length

  useEffect(() => {
    const unsub = subscribe((msg: WsMessage) => {
      if (msg.type === 'status_update') {
        const p = msg.payload as { state: string; detail?: string; constraint?: string; sprint_id?: number }
        const s = p.state
        if (s === 'ws_connected')    { setConnected(true);  setStatus('Connected') }
        else if (s === 'ws_disconnected') { setConnected(false); setStatus('Disconnected — reconnecting…') }
        else if (s === 'interrupted') {
          setStatus(`⚡ Interrupted: ${p.constraint || ''}`)
          setActiveStates(prev => {
            const next = { ...prev }
            Object.keys(next).forEach(k => { if (next[k] === 'running') next[k] = 'interrupted' })
            return next
          })
        } else if (s === 'sprint_running') {
          setStatus(`Sprint ${p.sprint_id} running…`)
        } else if (s === 'indexing') {
          setIndexing(true)
          setStatus(p.detail || 'Indexing codebase…')
        } else if (s === 'index_complete') {
          setIndexing(false)
          setStatus(p.detail || 'Indexing complete')
        } else {
          setStatus(p.detail || s)
        }
      }

      if (msg.type === 'sprint_graph') {
        const p = msg.payload as unknown as SprintGraph
        setGraph(p)
        const states: Record<string, string> = {}
        p.blueprint.nodes.forEach(n => { states[n.id] = 'idle' })
        setActiveStates(states)
        const total = p.sprints.reduce((a, s) => a + s.estimated_hours, 0)
        setStatus(`${p.sprints.length} sprints · ${total.toFixed(1)}h — awaiting approval`)
      }

      if (msg.type === 'error') {
        const p = msg.payload as { detail: string }
        setStatus(`Error: ${p.detail}`)
        setIndexing(false)
      }

      if (msg.type === 'clarification_needed') {
        const p = msg.payload as unknown as ClarificationState
        setClarification(p)
      }

      if (msg.type === 'agent_spawned') {
        const p = msg.payload as unknown as AgentSpawnEvent
        setDynAgents(prev => prev.find(a => a.agent_id === p.agent_id) ? prev : [...prev, p])
      }

      if (msg.type === 'api_call') {
        const ev = msg.payload as unknown as ApiCallEvent
        ev.timestamp = msg.timestamp
        const existing = callsRef.current.get(ev.call_id)
        if (ev.status === 'start') {
          callsRef.current.set(ev.call_id, ev)
        } else {
          callsRef.current.set(ev.call_id, { ...existing, ...ev })
          setTimeout(() => callsRef.current.delete(ev.call_id), 8_000)
        }
        setApiCalls(
          [...callsRef.current.values()]
            .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
            .slice(-MAX_CALLS)
        )
      }
    })
    return unsub
  }, [])

  const handleRedo = useCallback(() => {
    if (!graph) return
    setDynAgents([])
    send({ type: 'intent', payload: { text: graph.intent }, session_id: sessionId(), timestamp: new Date().toISOString() })
  }, [graph])

  const handleApprove = useCallback((sprintId: number) => {
    send({ type: 'sprint_approved', payload: { sprint_id: sprintId }, session_id: sessionId(), timestamp: new Date().toISOString() })
    if (!graph) return
    const sprint = graph.sprints.find((s: Sprint) => s.sprint_id === sprintId)
    if (!sprint) return
    setActiveStates(prev => {
      const next = { ...prev }
      sprint.node_ids.forEach(id => { next[id] = 'running' })
      return next
    })
    setStatus(`Sprint ${sprintId} running…`)
  }, [graph])

  function onDragStart(e: React.MouseEvent) {
    e.preventDefault()
    dragging.current = true
    dragStart.current = { y: e.clientY, h: terminalH }
    function onMove(ev: MouseEvent) {
      if (!dragging.current) return
      const delta = dragStart.current.y - ev.clientY
      setTerminalH(Math.min(TERMINAL_MAX, Math.max(TERMINAL_MIN, dragStart.current.h + delta)))
    }
    function onUp() {
      dragging.current = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'var(--bg)', position: 'relative' }}>

      {clarification && (
        <ClarificationPanel state={clarification} onDismiss={() => setClarification(null)} />
      )}

      <Header
        connected={connected}
        status={status}
        terminalOpen={terminalOpen}
        onToggleTerminal={() => setTerminalOpen(t => !t)}
      />

      {/* Main three-column body */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minHeight: 0 }}>

        <Settings />

        {/* Centre — tabs + graph */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>

          {/* Tab bar */}
          <div className="tab-bar">
            {([
              { id: 'graph',   label: 'Sprint Graph' },
              { id: 'apiflow', label: 'API Flow', badge: inFlightCount > 0 ? inFlightCount : undefined },
            ] as { id: Tab; label: string; badge?: number }[]).map(t => (
              <button
                key={t.id}
                className={`tab-btn${activeTab === t.id ? ' active' : ''}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
                {t.badge !== undefined && (
                  <span className="tab-badge">{t.badge}</span>
                )}
              </button>
            ))}
          </div>

          {/* Graph tab */}
          <div style={{ flex: 1, overflow: 'hidden', display: activeTab === 'graph' ? 'flex' : 'none', flexDirection: 'column' }}>
            {graph ? (
              <ReactFlowProvider>
                <SprintGraph_
                  blueprint={graph.blueprint}
                  sprints={graph.sprints}
                  onApprove={handleApprove}
                  activeStates={activeStates}
                  intent={graph.intent}
                  onRedo={handleRedo}
                />
              </ReactFlowProvider>
            ) : (
              <EmptyState />
            )}
          </div>

          {/* API flow tab */}
          <div style={{ flex: 1, overflow: 'hidden', display: activeTab === 'apiflow' ? 'flex' : 'none', flexDirection: 'column' }}>
            <ReactFlowProvider>
              <ApiFlowPanel calls={apiCalls} graph={graph} dynAgents={dynAgents} />
            </ReactFlowProvider>
          </div>
        </div>

        <ControlPanel status={status} indexing={indexing} setIndexing={setIndexing} />
      </div>

      {/* Terminal drag handle */}
      {terminalOpen && (
        <div
          onMouseDown={onDragStart}
          style={{
            height: 4, flexShrink: 0, cursor: 'row-resize',
            background: 'var(--border)', transition: 'background .15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--blue)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--border)')}
        />
      )}

      {terminalOpen && <TerminalPanel height={terminalH} />}
    </div>
  )
}

function EmptyState() {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 20,
      background: 'var(--bg)',
    }}>
      <div style={{ position: 'relative' }}>
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style={{ opacity: .18 }}>
          <polygon points="28,4 52,17 52,39 28,52 4,39 4,17"
            stroke="var(--blue)" strokeWidth="1.5" fill="none" strokeLinejoin="round" />
          <polygon points="28,16 40,22 40,34 28,40 16,34 16,22"
            stroke="var(--blue)" strokeWidth="1" fill="var(--bg-raised)" strokeLinejoin="round" />
          <circle cx="28" cy="28" r="4" fill="var(--blue)" />
        </svg>
        <div style={{
          position: 'absolute', inset: -8, borderRadius: '50%',
          background: 'radial-gradient(circle, var(--blue-glow) 0%, transparent 70%)',
          opacity: .4,
        }} />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 14, color: 'var(--text-2)', fontWeight: 600, marginBottom: 6 }}>
          No roadmap yet
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Enter an intent in the right panel<br />to generate a sprint graph
        </div>
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '7px 14px',
        background: 'var(--bg-raised)', border: '1px solid var(--border)',
        borderRadius: 99, fontSize: 11, color: 'var(--text-muted)',
      }}>
        <kbd style={{ fontFamily: 'var(--mono)', color: 'var(--blue)', fontSize: 11 }}>⌘↵</kbd>
        <span>to submit intent</span>
      </div>
    </div>
  )
}
