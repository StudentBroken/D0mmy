import { useState, useEffect } from 'react'
import { send, sessionId } from '../ws'
import type { VerifiedRef } from '../types'

interface Props { status: string; indexing: boolean; setIndexing: (v: boolean) => void }

export default function ControlPanel({ status, indexing, setIndexing }: Props) {
  const [intent,       setIntent]       = useState('')
  const [interrupt,    setInterrupt]    = useState('')
  const [verifyName,   setVerifyName]   = useState('')
  const [verifyResult, setVerifyResult] = useState<VerifiedRef | null>(null)
  const [verifying,    setVerifying]    = useState(false)
  const [indexStats,   setIndexStats]   = useState<{ modules?: number; total_files?: number; last_indexed?: string } | null>(null)

  function submitIntent() {
    const t = intent.trim(); if (!t) return
    send({ type: 'intent', payload: { text: t }, session_id: sessionId(), timestamp: new Date().toISOString() })
    setIntent('')
  }

  function submitInterrupt() {
    const t = interrupt.trim(); if (!t) return
    send({ type: 'interrupt', payload: { constraint: t }, session_id: sessionId(), timestamp: new Date().toISOString() })
    setInterrupt('')
  }

  async function submitVerify() {
    const n = verifyName.trim(); if (!n) return
    setVerifying(true); setVerifyResult(null)
    try {
      const r = await fetch(`/verify/${encodeURIComponent(n)}`)
      setVerifyResult(await r.json())
    } catch {
      setVerifyResult({ input_name: n, canonical: n, version: '?', kind: '?', verified: false, source: '', notes: 'Request failed', verified_at: Date.now() / 1000 })
    } finally { setVerifying(false) }
  }

  async function runIndex() {
    setIndexing(true)
    try {
      const r = await fetch('/index/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ force: false }) })
      if (!r.ok) {
        setIndexing(false)
        console.error('Failed to start indexer:', await r.text())
      }
    } catch (err) {
      setIndexing(false)
      console.error('Indexer error:', err)
    }
  }

  // Update stats whenever indexing finishes
  useEffect(() => {
    if (!indexing) {
      fetch('/index').then(r => r.json()).then(d => {
        setIndexStats({ modules: d.modules?.length, total_files: d.total_files, last_indexed: d.last_indexed })
      }).catch(() => {})
    }
  }, [indexing])

  const statusColor =
    status.startsWith('Error')                                        ? 'var(--red)'
    : status.includes('Interrupt')                                    ? 'var(--orange)'
    : status.includes('running') || status.includes('scouting') || status.includes('coding') ? 'var(--blue)'
    : status.includes('done') || status.includes('accepted')         ? 'var(--green)'
    : 'var(--text-2)'

  const isActive = status.includes('running') || status.includes('scouting') || status.includes('coding')

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      width: 'var(--ctrl-w)', minWidth: 'var(--ctrl-w)', flexShrink: 0,
      background: 'var(--bg-panel)', borderLeft: '1px solid var(--border)',
      height: '100%', overflowY: 'auto',
    }}>

      {/* ── Pipeline status ──────────────────────────────────────────── */}
      <div style={{
        padding: '12px 14px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-raised)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5 }}>
          <div style={{ position: 'relative', display: 'inline-flex' }}>
            {isActive && (
              <span style={{
                position: 'absolute', inset: -2, borderRadius: '50%',
                background: 'var(--blue)', opacity: .3,
                animation: 'pulse-ring 1.8s ease-out infinite',
              }} />
            )}
            <span className={`dot ${
              isActive ? 'dot-blue dot-pulse'
              : status.includes('done') || status.includes('accepted') ? 'dot-green'
              : status.startsWith('Error') ? 'dot-red'
              : status.includes('Interrupt') ? 'dot-orange'
              : 'dot-muted'
            }`} />
          </div>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Pipeline
          </span>
        </div>
        <div style={{
          fontSize: 11, color: statusColor,
          fontFamily: 'var(--mono)', lineHeight: 1.5,
          wordBreak: 'break-word',
        }}>
          {status}
        </div>
      </div>

      {/* ── Intent ───────────────────────────────────────────────────── */}
      <div className="panel-section">
        <label className="sec-label">Intent</label>
        <textarea
          placeholder="Describe what to build…"
          value={intent}
          onChange={e => setIntent(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submitIntent() }}
          style={{ marginBottom: 4, minHeight: 84 }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            {intent.length > 0 ? `${intent.length} chars` : ''}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>⌘↵ to run</span>
        </div>
        <button className="btn btn-primary" onClick={submitIntent} disabled={!intent.trim()}>
          ▶ Run Pipeline
        </button>
      </div>

      {/* ── Interrupt ────────────────────────────────────────────────── */}
      <div className="panel-section">
        <label className="sec-label">Interrupt</label>
        <input
          placeholder="New constraint to inject…"
          value={interrupt}
          onChange={e => setInterrupt(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') submitInterrupt() }}
          style={{ marginBottom: 8 }}
        />
        <button className="btn btn-orange" onClick={submitInterrupt} disabled={!interrupt.trim()}>
          ⚡ Inject Interrupt
        </button>
      </div>

      {/* ── Module Index ─────────────────────────────────────────────── */}
      <div className="panel-section">
        <label className="sec-label">Module Index</label>
        {indexStats ? (
          <div style={{
            display: 'flex', gap: 1, marginBottom: 8,
            background: 'var(--border)', borderRadius: 'var(--r)', overflow: 'hidden',
          }}>
            <div style={{ flex: 1, padding: '6px 9px', background: 'var(--bg-raised)' }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em' }}>Modules</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--cyan)' }}>{indexStats.modules ?? '?'}</div>
            </div>
            <div style={{ flex: 1, padding: '6px 9px', background: 'var(--bg-raised)' }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em' }}>Files</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--cyan)' }}>{indexStats.total_files ?? '?'}</div>
            </div>
          </div>
        ) : null}
        {indexStats?.last_indexed && (
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8 }}>
            Last indexed: {(() => { try { return new Date(indexStats.last_indexed!).toLocaleTimeString() } catch { return indexStats.last_indexed } })()}
          </div>
        )}
        <button className="btn btn-primary" onClick={runIndex} disabled={indexing}>
          {indexing
            ? <><span className="spin" style={{ display: 'inline-block' }}>↻</span> Indexing…</>
            : '↻ Index Codebase'}
        </button>
      </div>

      {/* ── Version Oracle ───────────────────────────────────────────── */}
      <div className="panel-section">
        <label className="sec-label">Version Oracle</label>
        <div style={{ display: 'flex', gap: 5, marginBottom: 0 }}>
          <input
            placeholder="gemini 3.1 pro, fastapi…"
            value={verifyName}
            onChange={e => setVerifyName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') submitVerify() }}
            style={{ flex: 1, marginBottom: 8 }}
          />
        </div>
        <button className="btn btn-purple" onClick={submitVerify} disabled={verifying || !verifyName.trim()}>
          {verifying
            ? <><span className="spin" style={{ display: 'inline-block' }}>↻</span> Verifying…</>
            : '🔍 Verify'}
        </button>

        {verifyResult && (
          <div className="verify-result fade-in">
            <div style={{ marginBottom: 7 }}>
              <span className={`badge ${verifyResult.verified ? 'badge-green' : 'badge-red'}`}>
                {verifyResult.verified ? '✓ VERIFIED' : '✗ UNVERIFIED'}
              </span>
            </div>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)', marginBottom: 3 }}>
              {verifyResult.canonical}
            </div>
            {verifyResult.version && !['N/A','unknown','latest'].includes(verifyResult.version) && (
              <div style={{ color: 'var(--text-2)', fontSize: 11, fontFamily: 'var(--mono)' }}>
                v{verifyResult.version}
              </div>
            )}
            {verifyResult.notes && (
              <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 6, lineHeight: 1.5 }}>
                {verifyResult.notes}
              </div>
            )}
            {verifyResult.source && (
              <a href={verifyResult.source} target="_blank" rel="noreferrer"
                style={{ color: 'var(--blue)', fontSize: 10, display: 'block', marginTop: 5, wordBreak: 'break-all' }}>
                ↗ {verifyResult.source}
              </a>
            )}
          </div>
        )}
      </div>

    </div>
  )
}
