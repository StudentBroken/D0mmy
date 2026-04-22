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
exports.DiffHandler = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
class DiffHandler {
    static SCHEME = 'd0mmy';
    _pending = null;
    _onResult = null;
    setResultCallback(cb) {
        this._onResult = cb;
    }
    _onDidChange = new vscode.EventEmitter();
    onDidChange = this._onDidChange.event;
    provideTextDocumentContent(uri) {
        // uri.path matches the filePath key stored in _pending
        if (this._pending && uri.path === this._pending.filePath) {
            return this._pending.content;
        }
        return '';
    }
    async showDiff(filePath, content, sessionId = 'ide') {
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
        await vscode.commands.executeCommand('vscode.diff', originalUri, proposedUri, `D0mmy ∆ ${path.basename(filePath)}  [Tab = accept  |  Esc = reject]`);
    }
    async accept() {
        if (!this._pending)
            return;
        const { filePath, content } = this._pending;
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
        const absolutePath = path.isAbsolute(filePath)
            ? filePath
            : path.join(workspaceRoot, filePath);
        const fileUri = vscode.Uri.file(absolutePath);
        const edit = new vscode.WorkspaceEdit();
        try {
            const doc = await vscode.workspace.openTextDocument(fileUri);
            const fullRange = new vscode.Range(doc.lineAt(0).range.start, doc.lineAt(doc.lineCount - 1).range.end);
            edit.replace(fileUri, fullRange, content);
        }
        catch {
            // File does not exist yet — create it
            edit.createFile(fileUri, { overwrite: true });
            edit.insert(fileUri, new vscode.Position(0, 0), content);
        }
        await vscode.workspace.applyEdit(edit);
        await this._cleanup(true);
    }
    async reject() {
        await this._cleanup(false);
    }
    async _cleanup(accepted) {
        const snapshot = this._pending;
        this._pending = null;
        await vscode.commands.executeCommand('setContext', 'd0mmy.diffPending', false);
        await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
        vscode.window.setStatusBarMessage(accepted ? '$(check) D0mmy diff accepted' : '$(x) D0mmy diff rejected', 3000);
        if (snapshot && this._onResult) {
            this._onResult(snapshot.filePath, accepted, snapshot.sessionId);
        }
    }
}
exports.DiffHandler = DiffHandler;
//# sourceMappingURL=diffHandler.js.map