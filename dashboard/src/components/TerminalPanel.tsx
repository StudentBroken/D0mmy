import { useEffect, useRef, useState, useCallback } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

const QUICK_CMDS = [
  { label: 'uv sync',          cmd: 'uv sync' },
  { label: 'setup keys',       cmd: 'python scripts/setup_keys.py' },
  { label: 'uv add pkg',       cmd: 'uv add ' },
  { label: 'python check',     cmd: 'python -c "from backend.config import get_settings; print(get_settings())"' },
  { label: 'chroma dump',      cmd: 'python -c "from backend.memory.hdd import fetch_context; import json; print(json.dumps(fetch_context(\'test\'), indent=2))"' },
]

interface Props {
  height: number
}

export default function TerminalPanel({ height }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const fitRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [cmd, setCmd] = useState('')
  const [running, setRunning] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const sessionId = useRef(`term-${Math.random().toString(36).slice(2, 8)}`)

  // Init xterm
  useEffect(() => {
    if (!containerRef.current) return

    const term = new Terminal({
      theme: {
        background: '#050a0f',
        foreground: '#c8d3e0',
        cursor: '#44aaff',
        selectionBackground: '#1a4a7a',
        black: '#1a1a2e', red: '#ff5566', green: '#44ff88',
        yellow: '#ffcc44', blue: '#44aaff', magenta: '#aa66ff',
        cyan: '#44ddff', white: '#c8d3e0',
        brightBlack: '#334455', brightRed: '#ff8899', brightGreen: '#88ffbb',
        brightYellow: '#ffdd77', brightBlue: '#77ccff', brightMagenta: '#cc99ff',
        brightCyan: '#77eeff', brightWhite: '#e8f0f8',
      },
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
      fontSize: 12,
      lineHeight: 1.4,
      cursorStyle: 'bar',
      cursorBlink: true,
      scrollback: 5000,
      convertEol: true,
    })

    const fit = new FitAddon()
    const links = new WebLinksAddon()
    term.loadAddon(fit)
    term.loadAddon(links)
    term.open(containerRef.current)
    fit.fit()
    termRef.current = term
    fitRef.current = fit

    // Forward keypresses to backend stdin
    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'input', data }))
      }
    })

    const ro = new ResizeObserver(() => fit.fit())
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      term.dispose()
    }
  }, [])

  // Resize xterm when panel height changes
  useEffect(() => {
    fitRef.current?.fit()
  }, [height])

  // WebSocket to backend terminal
  useEffect(() => {
    function connect() {
      const ws = new WebSocket(`ws://localhost:8000/ws/terminal/${sessionId.current}`)
      wsRef.current = ws

      ws.onopen = () => {
        setWsConnected(true)
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'output') {
            termRef.current?.write(msg.data)
          } else if (msg.type === 'started') {
            setRunning(true)
            termRef.current?.write(`\r\n\x1b[36m$ ${msg.cmd}\x1b[0m\r\n`)
          } else if (msg.type === 'exit') {
            setRunning(false)
            termRef.current?.write(`\r\n\x1b[33m[exit ${msg.code}]\x1b[0m\r\n`)
          } else if (msg.type === 'killed') {
            setRunning(false)
            termRef.current?.write('\r\n\x1b[31m[killed]\x1b[0m\r\n')
          }
        } catch { /* ignore */ }
      }

      ws.onclose = () => {
        setWsConnected(false)
        setRunning(false)
        setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const runCmd = useCallback((command: string) => {
    if (!command.trim() || !wsConnected) return
    wsRef.current?.send(JSON.stringify({ type: 'run', cmd: command }))
    setCmd('')
  }, [wsConnected])

  function killProcess() {
    wsRef.current?.send(JSON.stringify({ type: 'kill' }))
  }

  const btnBase: React.CSSProperties = {
    background: 'transparent', border: '1px solid', borderRadius: 3,
    fontSize: 11, padding: '3px 10px', cursor: 'pointer', fontFamily: 'inherit',
    whiteSpace: 'nowrap',
  }

  return (
    <div style={{
      height, display: 'flex', flexDirection: 'column',
      background: '#050a0f', borderTop: '1px solid #1a2a3a', flexShrink: 0,
    }}>
      {/* Toolbar */}
      <div style={{
        height: 34, display: 'flex', alignItems: 'center', gap: 6,
        padding: '0 10px', borderBottom: '1px solid #0f1a25', flexShrink: 0,
        overflowX: 'auto',
      }}>
        <span style={{ color: '#334', fontSize: 10, fontWeight: 700, letterSpacing: 1, marginRight: 4 }}>
          TERMINAL
        </span>
        <span style={{
          fontSize: 10, padding: '1px 6px', borderRadius: 8,
          background: wsConnected ? '#0d2a1a' : '#2a0d0d',
          color: wsConnected ? '#44ff88' : '#ff4444',
        }}>
          {wsConnected ? '●' : '○'}
        </span>

        {/* Quick-launch buttons */}
        {QUICK_CMDS.map(q => (
          <button key={q.label}
            style={{ ...btnBase, borderColor: '#1a3a5c', color: '#44aaff' }}
            onClick={() => runCmd(q.cmd)}>
            {q.label}
          </button>
        ))}

        <div style={{ flex: 1 }} />

        {running && (
          <button style={{ ...btnBase, borderColor: '#6a1a1a', color: '#ff6666' }} onClick={killProcess}>
            ⬛ Kill
          </button>
        )}
      </div>

      {/* xterm canvas */}
      <div ref={containerRef} style={{ flex: 1, overflow: 'hidden' }} />

      {/* Command input */}
      <div style={{
        height: 34, display: 'flex', alignItems: 'center', gap: 6,
        padding: '0 10px', borderTop: '1px solid #0f1a25', flexShrink: 0,
      }}>
        <span style={{ color: '#44aaff', fontSize: 12 }}>$</span>
        <input
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: '#c8d3e0', fontSize: 12, fontFamily: 'inherit',
          }}
          value={cmd}
          onChange={e => setCmd(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') runCmd(cmd) }}
          placeholder="run a command…"
          disabled={!wsConnected}
          spellCheck={false}
        />
        <button
          style={{ ...btnBase, borderColor: running ? '#6a1a1a' : '#1a4a2a', color: running ? '#ff6666' : '#44ff88' }}
          onClick={() => running ? killProcess() : runCmd(cmd)}>
          {running ? '⬛ Kill' : '▶ Run'}
        </button>
      </div>
    </div>
  )
}
