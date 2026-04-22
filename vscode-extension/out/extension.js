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
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const wsClient_1 = require("./wsClient");
const diffHandler_1 = require("./diffHandler");
let _wsClient = null;
let _contextThrottle = null;
function activate(context) {
    const machineId = vscode.env.machineId;
    _wsClient = new wsClient_1.WsClient(machineId);
    const diffHandler = new diffHandler_1.DiffHandler();
    const providerReg = vscode.workspace.registerTextDocumentContentProvider(diffHandler_1.DiffHandler.SCHEME, diffHandler);
    // Report diff accept/reject back to backend
    diffHandler.setResultCallback((filePath, accepted, sessionId) => {
        _wsClient?.send(accepted ? 'diff_accepted' : 'diff_rejected', { file_path: filePath }, sessionId);
    });
    // ── Incoming message handlers ──────────────────────────────────────────────
    _wsClient.on('ping', () => {
        _wsClient?.send('pong', {});
    });
    _wsClient.on('code_diff', (msg) => {
        const p = msg.payload;
        if (p?.file_path && p?.content !== undefined) {
            diffHandler.showDiff(p.file_path, p.content, p.session_id ?? 'ide');
        }
    });
    _wsClient.on('status_update', (msg) => {
        const p = msg.payload;
        if (p?.detail) {
            vscode.window.showInformationMessage(`D0mmy: ${p.detail}`);
        }
    });
    // ── Commands ───────────────────────────────────────────────────────────────
    const acceptCmd = vscode.commands.registerCommand('d0mmy.acceptDiff', () => {
        diffHandler.accept();
    });
    const rejectCmd = vscode.commands.registerCommand('d0mmy.rejectDiff', () => {
        diffHandler.reject();
    });
    const sendContextCmd = vscode.commands.registerCommand('d0mmy.sendContext', () => {
        void sendFileContext();
    });
    // ── Auto-send file context (throttled 500 ms) ──────────────────────────────
    const onEditorChange = vscode.window.onDidChangeActiveTextEditor(() => {
        _scheduleContext();
    });
    const onCursorChange = vscode.window.onDidChangeTextEditorSelection(() => {
        _scheduleContext();
    });
    _wsClient.connect();
    context.subscriptions.push(providerReg, acceptCmd, rejectCmd, sendContextCmd, onEditorChange, onCursorChange, { dispose: () => _wsClient?.dispose() });
}
function _scheduleContext() {
    if (_contextThrottle)
        clearTimeout(_contextThrottle);
    _contextThrottle = setTimeout(() => void sendFileContext(), 500);
}
async function sendFileContext() {
    if (!_wsClient)
        return;
    const editor = vscode.window.activeTextEditor;
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const sep = path.sep;
    let activeFile = null;
    let cursorLine = 0;
    let cursorCol = 0;
    if (editor) {
        const abs = editor.document.uri.fsPath;
        activeFile = workspaceRoot ? abs.replace(workspaceRoot + sep, '') : abs;
        cursorLine = editor.selection.active.line;
        cursorCol = editor.selection.active.character;
    }
    let workspaceFiles = [];
    if (workspaceRoot) {
        const uris = await vscode.workspace.findFiles('**/*', '{**/node_modules/**,**/.git/**,**/out/**,**/__pycache__/**}', 200);
        workspaceFiles = uris.map(u => u.fsPath.replace(workspaceRoot + sep, ''));
    }
    _wsClient.send('file_context', {
        active_file: activeFile,
        cursor_line: cursorLine,
        cursor_col: cursorCol,
        workspace_files: workspaceFiles,
    });
}
function deactivate() {
    _wsClient?.dispose();
}
//# sourceMappingURL=extension.js.map