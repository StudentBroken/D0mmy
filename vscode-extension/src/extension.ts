import * as vscode from 'vscode';
import * as path from 'path';
import { WsClient } from './wsClient';
import { DiffHandler } from './diffHandler';

let _wsClient: WsClient | null = null;
let _contextThrottle: ReturnType<typeof setTimeout> | null = null;

export function activate(context: vscode.ExtensionContext): void {
  const machineId = vscode.env.machineId;

  _wsClient = new WsClient(machineId);
  const diffHandler = new DiffHandler();

  const providerReg = vscode.workspace.registerTextDocumentContentProvider(
    DiffHandler.SCHEME,
    diffHandler,
  );

  // Report diff accept/reject back to backend
  diffHandler.setResultCallback((filePath, accepted, sessionId) => {
    _wsClient?.send(
      accepted ? 'diff_accepted' : 'diff_rejected',
      { file_path: filePath },
      sessionId,
    );
  });

  // ── Incoming message handlers ──────────────────────────────────────────────

  _wsClient.on('ping', () => {
    _wsClient?.send('pong', {});
  });

  _wsClient.on('code_diff', (msg) => {
    const p = msg.payload as { file_path?: string; content?: string; session_id?: string };
    if (p?.file_path && p?.content !== undefined) {
      diffHandler.showDiff(p.file_path, p.content, p.session_id ?? 'ide');
    }
  });

  _wsClient.on('status_update', (msg) => {
    const p = msg.payload as { state?: string; detail?: string };
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

  context.subscriptions.push(
    providerReg,
    acceptCmd,
    rejectCmd,
    sendContextCmd,
    onEditorChange,
    onCursorChange,
    { dispose: () => _wsClient?.dispose() },
  );
}

function _scheduleContext(): void {
  if (_contextThrottle) clearTimeout(_contextThrottle);
  _contextThrottle = setTimeout(() => void sendFileContext(), 500);
}

async function sendFileContext(): Promise<void> {
  if (!_wsClient) return;

  const editor = vscode.window.activeTextEditor;
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  const sep = path.sep;

  let activeFile: string | null = null;
  let cursorLine = 0;
  let cursorCol = 0;

  if (editor) {
    const abs = editor.document.uri.fsPath;
    activeFile = workspaceRoot ? abs.replace(workspaceRoot + sep, '') : abs;
    cursorLine = editor.selection.active.line;
    cursorCol  = editor.selection.active.character;
  }

  let workspaceFiles: string[] = [];
  if (workspaceRoot) {
    const uris = await vscode.workspace.findFiles(
      '**/*',
      '{**/node_modules/**,**/.git/**,**/out/**,**/__pycache__/**}',
      200,
    );
    workspaceFiles = uris.map(u => u.fsPath.replace(workspaceRoot + sep, ''));
  }

  _wsClient.send('file_context', {
    active_file:     activeFile,
    cursor_line:     cursorLine,
    cursor_col:      cursorCol,
    workspace_files: workspaceFiles,
  });
}

export function deactivate(): void {
  _wsClient?.dispose();
}
