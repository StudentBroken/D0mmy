import WebSocket from 'ws';
import * as vscode from 'vscode';

type MessageHandler = (msg: Record<string, unknown>) => void;

export class WsClient {
  private _ws: WebSocket | null = null;
  private _delay = 1000;
  private _maxDelay = 30_000;
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _disposed = false;
  private _handlers: Map<string, MessageHandler[]> = new Map();

  constructor(private readonly _machineId: string) {}

  get url(): string {
    const base = vscode.workspace
      .getConfiguration('d0mmy')
      .get<string>('backendUrl', 'ws://localhost:8000')
      .replace(/\/$/, '');
    return `${base}/ws/ide/${this._machineId}`;
  }

  connect(): void {
    if (this._disposed) return;

    this._ws = new WebSocket(this.url);

    this._ws.on('open', () => {
      this._delay = 1000;
      vscode.window.setStatusBarMessage('$(check) D0mmy connected', 3000);
    });

    this._ws.on('message', (data: WebSocket.RawData) => {
      try {
        const msg = JSON.parse(data.toString()) as Record<string, unknown>;
        const type = msg.type as string;
        this._handlers.get(type)?.forEach(h => h(msg));
        this._handlers.get('*')?.forEach(h => h(msg));
      } catch { /* ignore malformed frames */ }
    });

    this._ws.on('close', () => {
      this._ws = null;
      if (!this._disposed) this._scheduleReconnect();
    });

    this._ws.on('error', () => {
      this._ws?.terminate();
    });
  }

  on(type: string, handler: MessageHandler): void {
    const list = this._handlers.get(type) ?? [];
    list.push(handler);
    this._handlers.set(type, list);
  }

  send(type: string, payload: Record<string, unknown>, sessionId = 'ide'): void {
    if (this._ws?.readyState !== WebSocket.OPEN) return;
    this._ws.send(JSON.stringify({
      type,
      payload,
      session_id: sessionId,
      timestamp: new Date().toISOString(),
    }));
  }

  private _scheduleReconnect(): void {
    this._reconnectTimer = setTimeout(() => this.connect(), this._delay);
    this._delay = Math.min(this._delay * 2, this._maxDelay);
  }

  dispose(): void {
    this._disposed = true;
    if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
    this._ws?.close();
  }
}
