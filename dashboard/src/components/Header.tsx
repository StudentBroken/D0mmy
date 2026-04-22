import { useState, useEffect } from 'react'

interface Props {
  connected: boolean
  status: string
  terminalOpen: boolean
  onToggleTerminal: () => void
}

const CMD = `python dev.py   # starts launcher + dashboard\n# then click "Start Backend" in the header`

export default function Header({ connected, status, terminalOpen, onToggleTerminal }: Props) {
  const [showModal,      setShowModal]      = useState(false)
  const [launcherAlive,  setLauncherAlive]  = useState(false)
  const [backendOn,      setBackendOn]      = useState(false)
  const [busy,           setBusy]           = useState(false)
  const [copied,         setCopied]         = useState(false)
  const [targetRepo,     setTargetRepo]     = useState<string | null>(null)
  const [indexStats,     setIndexStats]     = useState<{ last_indexed?: string; total_files?: number } | null>(null)

  useEffect(() => {
    let alive = true
    async function poll() {
      while (alive) {
        try {
          const r = await fetch('/launcher/status')
          if (r.ok) { const d = await r.json(); setLauncherAlive(true); setBackendOn(d.running) }
          else setLauncherAlive(false)
        } catch { setLauncherAlive(false) }
        await new Promise(r => setTimeout(r, 3000))
      }
    }
    poll()
    return () => { alive = false }
  }, [])

  useEffect(() => {
    fetch('/settings').then(r => r.ok ? r.json() : null).then(d => {
      if (d?.settings?.TARGET_REPO) setTargetRepo(d.settings.TARGET_REPO)
    }).catch(() => {})

    fetch('/index').then(r => r.ok ? r.json() : null).then(d => {
      if (d) setIndexStats({ last_indexed: d.last_indexed, total_files: d.total_files })
    }).catch(() => {})
  }, [backendOn, status])

  async function toggleBackend() {
    setBusy(true)
    try {
      const r = await fetch(`/launcher/${backendOn ? 'stop' : 'start'}`)
      if (r.ok) { const d = await r.json(); setBackendOn(d.status === 'started' || d.status === 'already_running') }
    } finally { setBusy(false) }
  }

  async function syncEnv() {
    setBusy(true)
    try { await fetch('/launcher/sync') } finally { setBusy(false) }
  }

  const repoName = targetRepo ? targetRepo.split('/').pop() : null

  return (
    <>
      <header style={{
        height: 48, flexShrink: 0, zIndex: 100,
        background: 'var(--bg-panel)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10, padding: '0 14px',
      }}>

        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 2 }}>
          <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
            <polygon points="11,2 20,7 20,15 11,20 2,15 2,7"
              stroke="var(--blue)" strokeWidth="1.5" fill="none" strokeLinejoin="round" />
            <polygon points="11,7 16,9.5 16,14.5 11,17 6,14.5 6,9.5"
              stroke="var(--blue)" strokeWidth=".8" fill="var(--blue-dim)" strokeLinejoin="round" strokeOpacity=".5"/>
            <circle cx="11" cy="11" r="2" fill="var(--blue)" />
          </svg>
          <span style={{ fontWeight: 800, fontSize: 13, letterSpacing: '.14em', color: 'var(--text)' }}>
            D0MMY
          </span>
        </div>

        <div style={{ width: 1, height: 18, background: 'var(--border-hi)', flexShrink: 0 }} />

        {/* Connection */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 12, height: 12 }}>
            {connected && (
              <span style={{
                position: 'absolute', inset: -2, borderRadius: '50%',
                background: 'var(--green)', opacity: .3,
                animation: 'pulse-ring 1.8s ease-out infinite',
              }} />
            )}
            <span className={`dot ${connected ? 'dot-green' : 'dot-red'}`} />
          </div>
          <span style={{
            fontSize: 11, fontWeight: 600,
            color: connected ? 'var(--green)' : 'var(--red)',
          }}>
            {connected ? 'Live' : 'Offline'}
          </span>
        </div>

        {/* Repo badge */}
        {targetRepo && (
          <>
            <div style={{ width: 1, height: 14, background: 'var(--border-hi)', flexShrink: 0 }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '.05em', color: 'var(--text-muted)',
                textTransform: 'uppercase', flexShrink: 0
              }}>
                Repo:
              </span>
              <span style={{
                fontSize: 11, color: 'var(--text-2)',
                fontFamily: 'var(--mono)', maxWidth: 260,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                background: 'var(--bg-input)', padding: '2px 6px', borderRadius: 4,
                border: '1px solid var(--border)',
              }} title={targetRepo}>
                {targetRepo}
              </span>
            </div>
          </>
        )}

        {/* Index Status */}
        <div style={{ width: 1, height: 14, background: 'var(--border-hi)', flexShrink: 0 }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
           <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '.05em', color: 'var(--text-muted)',
                textTransform: 'uppercase', flexShrink: 0
              }}>
                Index:
              </span>
          {indexStats?.last_indexed ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className="badge badge-green" style={{ fontSize: 9, padding: '0 5px' }}>✓ Indexed</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
                {indexStats.total_files} files
              </span>
            </div>
          ) : (
            <span className="badge badge-red" style={{ fontSize: 9, padding: '0 5px' }}>✗ Unindexed</span>
          )}
        </div>

        {/* Status */}
        <span style={{
          flex: 1, fontSize: 11, color: 'var(--text-muted)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          fontFamily: 'var(--mono)', paddingLeft: 2,
        }}>
          {status}
        </span>

        {/* Right controls */}
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          <button
            className="btn-ghost"
            onClick={onToggleTerminal}
            style={{
              color: terminalOpen ? 'var(--blue)' : undefined,
              borderColor: terminalOpen ? 'var(--blue)' : undefined,
              fontSize: 11,
            }}
          >
            ⌨ Terminal
          </button>

          {launcherAlive ? (
            <>
              <button className="btn-ghost" onClick={syncEnv} disabled={busy} style={{ fontSize: 11 }}>
                {busy ? <span className="spin" style={{ display: 'inline-block' }}>↻</span> : '↻'} Sync
              </button>
              <button
                className="btn-ghost"
                onClick={toggleBackend}
                disabled={busy}
                style={{
                  borderColor: backendOn ? 'var(--red)' : 'var(--green)',
                  color: backendOn ? 'var(--red)' : 'var(--green)',
                  fontSize: 11,
                }}
              >
                {busy ? '…' : backendOn ? '■ Stop' : '▶ Start'}
              </button>
            </>
          ) : (
            <button
              className="btn-ghost"
              style={{ color: 'var(--text-muted)', borderColor: 'var(--border)', fontSize: 11 }}
              onClick={() => setShowModal(true)}
            >
              ▶ Start Backend
            </button>
          )}

          <button className="btn-ghost" onClick={() => setShowModal(true)} style={{ fontSize: 11 }}>
            ? Help
          </button>
        </div>
      </header>

      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <span className="modal__title">Getting Started</span>
              <button className="btn-ghost" onClick={() => setShowModal(false)} style={{ padding: '3px 9px' }}>✕</button>
            </div>
            <div className="modal__body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <p style={{ color: 'var(--text-2)', fontSize: 12, lineHeight: 1.7 }}>
                D0mmy needs two processes: the Python backend (FastAPI on :8000) and this dashboard (Vite on :5173).
              </p>

              <pre className="code-block">{CMD}</pre>

              <button
                className="btn-ghost"
                style={{ alignSelf: 'flex-start', color: copied ? 'var(--green)' : undefined }}
                onClick={() => { navigator.clipboard.writeText(CMD); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
              >
                {copied ? '✓ Copied' : '⎘ Copy command'}
              </button>

              <div style={{
                padding: '12px 14px', background: 'var(--bg-input)',
                border: '1px solid var(--border)', borderRadius: 'var(--r)',
              }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 700 }}>
                  Launcher status
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className={`dot ${launcherAlive ? 'dot-green' : 'dot-muted'}`} />
                  <span style={{ fontSize: 12, color: launcherAlive ? 'var(--green)' : 'var(--text-muted)' }}>
                    {launcherAlive
                      ? `Launcher running — backend ${backendOn ? 'active' : 'stopped'}`
                      : 'Not running — run python scripts/launcher.py'}
                  </span>
                </div>
              </div>

              <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                <strong style={{ color: 'var(--text-2)' }}>Keyboard shortcuts</strong><br />
                <code style={{ fontFamily: 'var(--mono)', color: 'var(--cyan)' }}>⌘↵</code> — Submit intent &nbsp;·&nbsp;
                <code style={{ fontFamily: 'var(--mono)', color: 'var(--cyan)' }}>Tab</code> — Accept diff &nbsp;·&nbsp;
                <code style={{ fontFamily: 'var(--mono)', color: 'var(--cyan)' }}>Esc</code> — Reject diff
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
