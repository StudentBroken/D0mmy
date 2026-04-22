import { useState, useEffect } from 'react'
import type { VerifiedRef } from '../types'

type Tab = 'api' | 'models' | 'server' | 'hardware'
type ProjectMode = 'software' | 'hardware+software'

const TAB_META: { id: Tab; icon: string; label: string }[] = [
  { id: 'api',      icon: '⌗', label: 'API Key'  },
  { id: 'models',   icon: '◈', label: 'Models'   },
  { id: 'server',   icon: '⬡', label: 'Server'   },
  { id: 'hardware', icon: '⬢', label: 'Hardware' },
]

export default function Settings() {
  const [collapsed,       setCollapsed]       = useState(false)
  const [tab,             setTab]             = useState<Tab>('api')
  const [fields,          setFields]          = useState<Record<string, string>>({})
  const [apiKeyInput,     setApiKeyInput]     = useState('')
  const [apiKeySet,       setApiKeySet]       = useState(false)
  const [bom,             setBom]             = useState('')
  const [saved,           setSaved]           = useState(false)
  const [saveError,       setSaveError]       = useState('')
  const [loading,         setLoading]         = useState(true)
  const [projectMode,     setProjectModeState]= useState<ProjectMode>('software')
  const [modeSaving,      setModeSaving]      = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const [r, br, mr] = await Promise.all([
          fetch('/settings'),
          fetch('/settings/bom'),
          fetch('/settings/mode'),
        ])
        if (r.ok) {
          const d = await r.json()
          const s = d.settings || {}
          setFields(s)
          setApiKeySet(Boolean(s['GOOGLE_API_KEY']))
        }
        if (br.ok) setBom(JSON.stringify(await br.json(), null, 2))
        if (mr.ok) setProjectModeState((await mr.json()).project_mode || 'software')
      } finally { setLoading(false) }
    }
    load()
  }, [])

  async function switchMode(mode: ProjectMode) {
    if (mode === projectMode) return
    setModeSaving(true)
    try {
      const r = await fetch('/settings/mode', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_mode: mode }),
      })
      if (r.ok) {
        setProjectModeState(mode)
        if (mode === 'software' && tab === 'hardware') setTab('api')
      }
    } finally { setModeSaving(false) }
  }

  function setField(key: string, val: string) {
    setFields(f => ({ ...f, [key]: val }))
  }

  async function save(keys: string[]) {
    const updates: Record<string, string> = {}
    keys.forEach(k => { if (fields[k] !== undefined) updates[k] = fields[k] })
    const r = await fetch('/settings', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates }),
    })
    if (r.ok) { flashSaved() } else { setSaveError(`Save failed (${r.status})`) }
  }

  async function saveApiKey() {
    if (!apiKeyInput.trim()) return
    const r = await fetch('/settings', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates: { GOOGLE_API_KEY: apiKeyInput.trim() } }),
    })
    if (r.ok) { setApiKeySet(true); setApiKeyInput(''); flashSaved() }
  }

  async function saveBom() {
    setSaveError('')
    let parsed: unknown
    try { parsed = JSON.parse(bom) }
    catch { setSaveError('Invalid JSON — fix syntax before saving'); return }
    const r = await fetch('/settings/bom', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bom: parsed }),
    })
    if (!r.ok) {
      const d = await r.json().catch(() => ({ detail: `HTTP ${r.status}` }))
      setSaveError(d.detail || `Save failed`)
      return
    }
    const confirm = await fetch('/settings/bom')
    if (confirm.ok) setBom(JSON.stringify(await confirm.json(), null, 2))
    flashSaved()
  }

  function flashSaved() {
    setSaved(true); setSaveError('')
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) return (
    <div className="sidebar sidebar--expanded" style={{ alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>Loading…</span>
    </div>
  )

  /* ── Collapsed mode ─────────────────────────────────────────────────────── */
  if (collapsed) return (
    <div className="sidebar sidebar--collapsed">
      <button
        className="sidebar-icon-btn"
        onClick={() => setCollapsed(false)}
        title="Expand settings"
        style={{ height: 48, fontSize: 13, borderBottom: '1px solid var(--border)' }}
      >
        ▷
      </button>

      {/* Mode dot */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 36 }}>
        <span
          className={`dot ${projectMode === 'hardware+software' ? 'dot-orange' : 'dot-blue'}`}
          title={`Mode: ${projectMode}`}
        />
      </div>

      <div style={{ height: 1, background: 'var(--border)', margin: '2px 0' }} />

      {/* Tab icons */}
      {TAB_META.map(t => {
        const disabled = t.id === 'hardware' && projectMode === 'software'
        return (
          <button
            key={t.id}
            className={`sidebar-icon-btn${tab === t.id && !collapsed ? ' active' : ''}`}
            title={t.label}
            disabled={disabled}
            onClick={() => { setCollapsed(false); setTab(t.id) }}
            style={{ opacity: disabled ? .3 : 1, fontSize: 15 }}
          >
            {t.icon}
          </button>
        )
      })}

      <div style={{ flex: 1 }} />

      {(saved || saveError) && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0' }}>
          <span className={`dot ${saved ? 'dot-green' : 'dot-red'}`} />
        </div>
      )}
    </div>
  )

  /* ── Expanded mode ──────────────────────────────────────────────────────── */
  return (
    <div className="sidebar sidebar--expanded">

      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 12px', height: 48, flexShrink: 0,
        borderBottom: '1px solid var(--border)',
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          Settings
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {saved && <span className="fade-in" style={{ fontSize: 10, color: 'var(--green)', fontWeight: 600 }}>✓ Saved</span>}
          {saveError && !saved && <span className="fade-in" style={{ fontSize: 10, color: 'var(--red)' }}>✗ Error</span>}
          <button className="btn-icon" onClick={() => setCollapsed(true)} title="Collapse" style={{ fontSize: 11 }}>◁</button>
        </div>
      </div>

      {/* Mode toggle */}
      <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <div className="sec-label">Project Mode</div>
        <div style={{ display: 'flex', gap: 5, opacity: modeSaving ? .6 : 1 }}>
          {([
            { value: 'software',           label: 'Software', color: 'var(--blue)' },
            { value: 'hardware+software',  label: 'HW + SW',  color: 'var(--orange)' },
          ] as const).map(m => {
            const active = projectMode === m.value
            return (
              <button
                key={m.value}
                onClick={() => switchMode(m.value)}
                disabled={modeSaving}
                style={{
                  flex: 1, padding: '6px 0', fontSize: 11, fontWeight: 600,
                  background: active ? m.color + '22' : 'transparent',
                  border: `1px solid ${active ? m.color : 'var(--border-hi)'}`,
                  borderRadius: 'var(--r)', color: active ? m.color : 'var(--text-muted)',
                  cursor: 'pointer', fontFamily: 'var(--sans)', transition: 'all .15s',
                }}
              >
                {m.label}
              </button>
            )
          })}
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.5 }}>
          {projectMode === 'software' ? 'BOM + serial daemon disabled.' : 'BOM validation + serial daemon active.'}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        {TAB_META.map(t => {
          const disabled = t.id === 'hardware' && projectMode === 'software'
          const active = tab === t.id
          return (
            <button
              key={t.id}
              style={{
                flex: 1, background: 'none', border: 'none',
                borderBottom: active ? '2px solid var(--blue)' : '2px solid transparent',
                color: disabled ? 'var(--text-muted)' : active ? 'var(--text)' : 'var(--text-muted)',
                fontSize: 10, fontWeight: active ? 700 : 500,
                padding: '8px 2px', cursor: disabled ? 'not-allowed' : 'pointer',
                fontFamily: 'var(--sans)', transition: 'color .12s', letterSpacing: '.02em',
                marginBottom: -1,
              }}
              onClick={() => !disabled && setTab(t.id)}
            >
              {t.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 13 }}>

        {tab === 'api' && (
          <div className="slide-in" key="api">
            <div style={{ marginBottom: 14 }}>
              <label className="sec-label">Google AI API Key</label>
              {apiKeySet && (
                <div className="info-box info-box--green" style={{ marginBottom: 8 }}>
                  ✓ Key configured — enter a new value to replace
                </div>
              )}
              <input
                type="password"
                value={apiKeyInput}
                onChange={e => setApiKeyInput(e.target.value)}
                placeholder={apiKeySet ? '(leave blank to keep)' : 'AIzaSy…'}
                autoComplete="off"
                onKeyDown={e => { if (e.key === 'Enter') saveApiKey() }}
                style={{ marginBottom: 6 }}
              />
              <div style={{ fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Get key at{' '}
                <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer"
                  style={{ color: 'var(--blue)' }}>aistudio.google.com</a>
              </div>
            </div>
            <button
              className="btn btn-primary"
              style={{ opacity: apiKeyInput.trim() ? 1 : .4 }}
              onClick={saveApiKey}
              disabled={!apiKeyInput.trim()}
            >
              {apiKeySet ? 'Replace Key' : 'Save Key'}
            </button>
          </div>
        )}

        {tab === 'models' && (
          <div className="slide-in" key="models">
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 12, lineHeight: 1.6 }}>
              Click 🔍 to verify each model ID via the Version Oracle.
            </div>
            <FieldWithVerify label="Heavy (Gemini 3.1 Pro)"
              value={fields['HEAVY_MODEL'] || ''} onChange={v => setField('HEAVY_MODEL', v)} />
            <FieldWithVerify label="Worker (Gemma 4 31B)"
              value={fields['WORKER_MODEL'] || ''} onChange={v => setField('WORKER_MODEL', v)} />
            <FieldWithVerify label="Daemon (Gemma 4 26B MoE)"
              value={fields['DAEMON_MODEL'] || ''} onChange={v => setField('DAEMON_MODEL', v)} />
            <FieldWithVerify label="Embedding"
              value={fields['EMBEDDING_MODEL'] || ''} onChange={v => setField('EMBEDDING_MODEL', v)} />
            <button className="btn btn-primary" onClick={() => save(['HEAVY_MODEL','WORKER_MODEL','DAEMON_MODEL','EMBEDDING_MODEL'])}>
              Save All Models
            </button>
          </div>
        )}

        {tab === 'server' && (
          <div className="slide-in" key="server">
            <FormField label="Backend Host">
              <input value={fields['BACKEND_HOST'] || '127.0.0.1'} onChange={e => setField('BACKEND_HOST', e.target.value)} />
            </FormField>
            <FormField label="Backend Port">
              <input value={fields['BACKEND_PORT'] || '8000'} onChange={e => setField('BACKEND_PORT', e.target.value)} />
            </FormField>
            <FormField label="ChromaDB Directory">
              <input value={fields['CHROMA_PERSIST_DIR'] || './data/chroma'} onChange={e => setField('CHROMA_PERSIST_DIR', e.target.value)} />
            </FormField>
            <FormField label="Target Repo" hint="Leave empty for self-hosted mode">
              <input value={fields['TARGET_REPO'] || ''} onChange={e => setField('TARGET_REPO', e.target.value)} placeholder="(none — D0mmy directory)" />
            </FormField>
            <FormField label="Log Level">
              <select value={fields['LOG_LEVEL'] || 'INFO'} onChange={e => setField('LOG_LEVEL', e.target.value)}>
                {['DEBUG','INFO','WARNING','ERROR'].map(l => <option key={l}>{l}</option>)}
              </select>
            </FormField>
            <button className="btn btn-primary" onClick={() => save(['BACKEND_HOST','BACKEND_PORT','CHROMA_PERSIST_DIR','TARGET_REPO','LOG_LEVEL'])}>
              Save Server Settings
            </button>
            {saveError && <div className="info-box info-box--red" style={{ marginTop: 8 }}>✗ {saveError}</div>}
          </div>
        )}

        {tab === 'hardware' && (
          <div className="slide-in" key="hardware">
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 10, lineHeight: 1.6 }}>
              Hardware BOM — JSON. Every agent validates generated code against this.
            </div>
            {projectMode === 'software' && (
              <div className="info-box info-box--amber" style={{ marginBottom: 10 }}>
                Switch to HW+SW mode to enable BOM validation.
              </div>
            )}
            <textarea
              style={{
                fontFamily: 'var(--mono)', fontSize: 11, resize: 'vertical', minHeight: 220,
                borderColor: saveError ? 'var(--red)' : undefined,
              }}
              value={bom}
              onChange={e => { setBom(e.target.value); setSaveError('') }}
              spellCheck={false}
            />
            {saveError && <div className="info-box info-box--red" style={{ marginTop: 6 }}>✗ {saveError}</div>}
            <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={saveBom}>Save BOM</button>
          </div>
        )}

      </div>
    </div>
  )
}

/* ── Field helpers ─────────────────────────────────────────────────────────── */

function FormField({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 13 }}>
      <label className="sec-label">{label}</label>
      {hint && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 5 }}>{hint}</div>}
      {children}
    </div>
  )
}

function FieldWithVerify({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const [ref, setRef] = useState<VerifiedRef | null>(null)
  const [busy, setBusy] = useState(false)

  async function verify() {
    if (!value) return
    setBusy(true); setRef(null)
    try {
      const r = await fetch(`/verify/${encodeURIComponent(value)}`)
      setRef(await r.json())
    } finally { setBusy(false) }
  }

  return (
    <div style={{ marginBottom: 13 }}>
      <label className="sec-label">{label}</label>
      <div style={{ display: 'flex', gap: 5 }}>
        <input value={value} onChange={e => onChange(e.target.value)} style={{ flex: 1 }}
          onKeyDown={e => { if (e.key === 'Enter') verify() }} />
        <button
          className="btn-icon"
          onClick={verify}
          disabled={busy || !value}
          title="Verify via Version Oracle"
          style={{ width: 32, height: 32, fontSize: 12, flexShrink: 0 }}
        >
          {busy ? <span className="spin" style={{ display: 'inline-block' }}>↻</span> : '🔍'}
        </button>
      </div>
      {ref && (
        <div className="verify-result">
          <span className={`badge ${ref.verified ? 'badge-green' : 'badge-red'}`} style={{ fontSize: 10 }}>
            {ref.verified ? `✓ ${ref.canonical}` : '✗ unverified'}
          </span>
          {ref.verified && ref.canonical !== value && (
            <span style={{ fontSize: 10, color: 'var(--orange)', marginLeft: 8 }}>≠ consider updating</span>
          )}
          {ref.notes && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>{ref.notes}</div>}
        </div>
      )}
    </div>
  )
}
