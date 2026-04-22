import type { WsMessage } from './types'

const SESSION_ID = `dash-${Math.random().toString(36).slice(2, 9)}`

// Use the backend host directly; Vite dev proxy doesn't handle WebSockets for
// arbitrary paths reliably, so we connect straight to port 8000.
const WS_BASE = `ws://localhost:8000`
const WS_URL  = `${WS_BASE}/ws/dashboard/${SESSION_ID}`

const RECONNECT_BASE_MS  = 1_000
const RECONNECT_MAX_MS   = 30_000

type Handler = (msg: WsMessage) => void

let socket: WebSocket | null = null
let handlers: Handler[] = []
let pendingOut: object[] = []
let _connected = false
let _retryCount = 0
let _retryTimer: ReturnType<typeof setTimeout> | null = null

function _backoff(): number {
  return Math.min(RECONNECT_BASE_MS * 2 ** _retryCount, RECONNECT_MAX_MS)
}

function _emit(msg: WsMessage) {
  handlers.forEach(h => h(msg))
}

function connect() {
  if (_retryTimer) { clearTimeout(_retryTimer); _retryTimer = null }

  socket = new WebSocket(WS_URL)

  socket.onopen = () => {
    _connected = true
    _retryCount = 0
    pendingOut.forEach(m => socket!.send(JSON.stringify(m)))
    pendingOut = []
    _emit({ type: 'status_update', payload: { state: 'ws_connected' }, session_id: SESSION_ID, timestamp: new Date().toISOString() })
  }

  socket.onmessage = (ev) => {
    try {
      const msg: WsMessage = JSON.parse(ev.data)
      if (msg.type === 'ping') {
        // Reply immediately so the server keepalive sees us as alive
        socket?.send(JSON.stringify({ type: 'pong', session_id: SESSION_ID, timestamp: new Date().toISOString() }))
        return
      }
      _emit(msg)
    } catch { /* ignore malformed */ }
  }

  socket.onclose = (_ev) => {
    _connected = false
    _emit({ type: 'status_update', payload: { state: 'ws_disconnected' }, session_id: SESSION_ID, timestamp: new Date().toISOString() })
    const delay = _backoff()
    _retryCount = Math.min(_retryCount + 1, 10)
    _retryTimer = setTimeout(connect, delay)
  }

  socket.onerror = () => {
    // onclose fires after onerror; let it handle retry
    socket?.close()
  }
}

export function send(msg: object) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg))
  } else {
    pendingOut.push(msg)
  }
}

export function subscribe(handler: Handler): () => void {
  handlers.push(handler)
  // Replay current connection state so late subscribers don't miss the open event
  if (_connected) {
    handler({
      type: 'status_update',
      payload: { state: 'ws_connected' },
      session_id: SESSION_ID,
      timestamp: new Date().toISOString(),
    })
  }
  return () => { handlers = handlers.filter(h => h !== handler) }
}

export function isConnected() { return _connected }
export function sessionId() { return SESSION_ID }

connect()
