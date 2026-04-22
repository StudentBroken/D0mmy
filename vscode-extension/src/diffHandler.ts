import * as vscode from 'vscode';
import * as path from 'path';

interface PendingDiff {
  filePath: string;
  content: string;
  sessionId: string;
}

type ResultCallback = (filePath: string, accepted: boolean, sessionId: string) => void;

export class DiffHandler implements vscode.TextDocumentContentProvider {
  static readonly SCHEME = 'd0mmy';

  private _pending: PendingDiff | null = null;
  private _onResult: ResultCallback | null = null;

  setResultCallback(cb: ResultCallback): void {
    this._onResult = cb;
  }
  private _onDidChange = new vscode.EventEmitter<vscode.Uri>();
  readonly onDidChange = this._onDidChange.event;

  provideTextDocumentContent(uri: vscode.Uri): string {
    // uri.path matches the filePath key stored in _pending
    if (this._pending && uri.path === this._pending.filePath) {
      return this._pending.content;
    }
    return '';
  }

  async showDiff(filePath: string, content: string, sessionId = 'ide'): Promise<void> {
    // Discard any previous pending diff
    if (this._pending) {
      await this._cleanup(false);
    }

    this._pending = { filePath, content, sessionId };
    await vscode.commands.executeCommand('setContext', 'd0mmy.diffPending', true);

    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
    const absolutePath = path.isAbsolute(filePath)
      ? filePath
      : path.join(workspaceRoot, filePath);

    const originalUri = vscode.Uri.file(absolutePath);
    // Use filePath as the virtual URI path so provideTextDocumentContent can match it
    const proposedUri = vscode.Uri.from({ scheme: DiffHandler.SCHEME, path: filePath });
    this._onDidChange.fire(proposedUri);

    await vscode.commands.executeCommand(
      'vscode.diff',
      originalUri,
      proposedUri,
      `D0mmy ∆ ${path.basename(filePath)}  [Tab = accept  |  Esc = reject]`,
    );
  }

  async accept(): Promise<void> {
    if (!this._pending) return;
    const { filePath, content } = this._pending;

    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
    const absolutePath = path.isAbsolute(filePath)
      ? filePath
      : path.join(workspaceRoot, filePath);

    const fileUri = vscode.Uri.file(absolutePath);
    const edit = new vscode.WorkspaceEdit();

    try {
      const doc = await vscode.workspace.openTextDocument(fileUri);
      const fullRange = new vscode.Range(
        doc.lineAt(0).range.start,
        doc.lineAt(doc.lineCount - 1).range.end,
      );
      edit.replace(fileUri, fullRange, content);
    } catch {
      // File does not exist yet — create it
      edit.createFile(fileUri, { overwrite: true });
      edit.insert(fileUri, new vscode.Position(0, 0), content);
    }

    await vscode.workspace.applyEdit(edit);
    await this._cleanup(true);
  }

  async reject(): Promise<void> {
    await this._cleanup(false);
  }

  private async _cleanup(accepted: boolean): Promise<void> {
    const snapshot = this._pending;
    this._pending = null;
    await vscode.commands.executeCommand('setContext', 'd0mmy.diffPending', false);
    await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
    vscode.window.setStatusBarMessage(
      accepted ? '$(check) D0mmy diff accepted' : '$(x) D0mmy diff rejected',
      3000,
    );
    if (snapshot && this._onResult) {
      this._onResult(snapshot.filePath, accepted, snapshot.sessionId);
    }
  }
}
