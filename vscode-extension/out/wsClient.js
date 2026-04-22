"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.WsClient = void 0;
const ws_1 = __importDefault(require("ws"));
const vscode = __importStar(require("vscode"));
class WsClient {
    _machineId;
    _ws = null;
    _delay = 1000;
    _maxDelay = 30_000;
    _reconnectTimer = null;
    _disposed = false;
    _handlers = new Map();
    constructor(_machineId) {
        this._machineId = _machineId;
    }
    get url() {
        return `ws://localhost:8000/ws/ide/${this._machineId}`;
    }
    connect() {
        if (this._disposed)
            return;
        this._ws = new ws_1.default(this.url);
        this._ws.on('open', () => {
            this._delay = 1000;
            vscode.window.setStatusBarMessage('$(check) D0mmy connected', 3000);
        });
        this._ws.on('message', (data) => {
            try {
                const msg = JSON.parse(data.toString());
                const type = msg.type;
                this._handlers.get(type)?.forEach(h => h(msg));
                this._handlers.get('*')?.forEach(h => h(msg));
            }
            catch { /* ignore malformed frames */ }
        });
        this._ws.on('close', () => {
            this._ws = null;
            if (!this._disposed)
                this._scheduleReconnect();
        });
        this._ws.on('error', () => {
            this._ws?.terminate();
        });
    }
    on(type, handler) {
        const list = this._handlers.get(type) ?? [];
        list.push(handler);
        this._handlers.set(type, list);
    }
    send(type, payload, sessionId = 'ide') {
        if (this._ws?.readyState !== ws_1.default.OPEN)
            return;
        this._ws.send(JSON.stringify({
            type,
            payload,
            session_id: sessionId,
            timestamp: new Date().toISOString(),
        }));
    }
    _scheduleReconnect() {
        this._reconnectTimer = setTimeout(() => this.connect(), this._delay);
        this._delay = Math.min(this._delay * 2, this._maxDelay);
    }
    dispose() {
        this._disposed = true;
        if (this._reconnectTimer)
            clearTimeout(this._reconnectTimer);
        this._ws?.close();
    }
}
exports.WsClient = WsClient;
//# sourceMappingURL=wsClient.js.map