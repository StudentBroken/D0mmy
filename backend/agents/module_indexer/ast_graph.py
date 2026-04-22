"""
AST-based import and symbol extractor.
Python: uses stdlib `ast`. TypeScript/JS: regex-based (no Node dependency).
Returns FileGraph with symbols (name, line, kind) and import paths.
"""
from __future__ import annotations
import ast
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Symbol:
    name: str
    line: int
    kind: str           # function | class | method | interface
    parent: str | None = None


@dataclass
class FileGraph:
    path: str           # relative path
    checksum: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str]  = field(default_factory=list)


def _checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


# ── Python ────────────────────────────────────────────────────────────────────

def _parse_python(rel_path: str, content: str) -> FileGraph:
    chk = _checksum(content.encode())
    symbols: list[Symbol] = []
    imports: list[str] = []

    try:
        tree = ast.parse(content, filename=rel_path)
    except SyntaxError:
        return FileGraph(path=rel_path, checksum=chk)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, ast.ClassDef):
            symbols.append(Symbol(node.name, node.lineno, "class"))
            for item in ast.walk(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item is not node:
                    symbols.append(Symbol(item.name, item.lineno, "method", parent=node.name))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip methods — already captured under their class above
            if not any(
                isinstance(p, ast.ClassDef) and node in ast.walk(p)
                for p in ast.walk(tree)
                if isinstance(p, ast.ClassDef) and p is not node
            ):
                symbols.append(Symbol(node.name, node.lineno, "function"))

    return FileGraph(rel_path, chk, symbols, list(dict.fromkeys(imports)))


# ── TypeScript / JavaScript ───────────────────────────────────────────────────

_TS_IMPORT  = re.compile(r"""from\s+['"]([^'"]+)['"]""")
_TS_FUNC    = re.compile(r"""(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[(<]""")
_TS_ARROW   = re.compile(r"""(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(""")
_TS_CLASS   = re.compile(r"""(?:export\s+)?(?:default\s+)?class\s+(\w+)""")
_TS_IFACE   = re.compile(r"""(?:export\s+)?(?:interface|type)\s+(\w+)\s*[={<]""")
_TS_METHOD  = re.compile(r"""^\s{2,}(?:async\s+)?(\w+)\s*\(""")


    return FileGraph(rel_path, chk, symbols, list(dict.fromkeys(imports)))


def _parse_typescript(rel_path: str, content: str) -> FileGraph:
    chk = _checksum(content.encode())
    symbols: list[Symbol] = []
    imports: list[str] = []
    current_class: str | None = None

    for i, line in enumerate(content.splitlines(), start=1):
        for m in _TS_IMPORT.finditer(line):
            imports.append(m.group(1))

        if m := _TS_CLASS.search(line):
            current_class = m.group(1)
            symbols.append(Symbol(current_class, i, "class"))
        elif m := _TS_IFACE.search(line):
            symbols.append(Symbol(m.group(1), i, "interface"))
        elif m := _TS_FUNC.search(line):
            symbols.append(Symbol(m.group(1), i, "function"))
        elif m := _TS_ARROW.search(line):
            symbols.append(Symbol(m.group(1), i, "function"))
        elif current_class and (m := _TS_METHOD.match(line)):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch", "return", "const", "let"}:
                symbols.append(Symbol(name, i, "method", parent=current_class))

        # Simple heuristic: class body ends when we hit a top-level closing brace
        if current_class and line.startswith("}"):
            current_class = None

    return FileGraph(rel_path, chk, symbols, list(dict.fromkeys(imports)))


# ── Dart ──────────────────────────────────────────────────────────────────────

_DART_IMPORT = re.compile(r"""import\s+['"]([^'"]+)['"]""")
_DART_CLASS  = re.compile(r"""(?:abstract\s+)?class\s+(\w+)""")
_DART_FUNC   = re.compile(r"""^(?:\w+[\s<][^>]*>?\s+)?(\w+)\s*\(""")


def _parse_dart(rel_path: str, content: str) -> FileGraph:
    chk = _checksum(content.encode())
    symbols: list[Symbol] = []
    imports: list[str] = []
    current_class: str | None = None

    for i, line in enumerate(content.splitlines(), start=1):
        line_trim = line.strip()
        if m := _DART_IMPORT.search(line):
            imports.append(m.group(1))

        if m := _DART_CLASS.search(line):
            current_class = m.group(1)
            symbols.append(Symbol(current_class, i, "class"))
        elif m := _DART_FUNC.search(line_trim):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch", "return", "void", "else", "try", "catch"}:
                kind = "method" if current_class else "function"
                symbols.append(Symbol(name, i, kind, parent=current_class))

        if current_class and line_trim == "}":
            current_class = None

    return FileGraph(rel_path, chk, symbols, list(dict.fromkeys(imports)))


# ── Dispatcher ────────────────────────────────────────────────────────────────

_PARSERS = {
    ".py":   _parse_python,
    ".ts":   _parse_typescript,
    ".tsx":  _parse_typescript,
    ".js":   _parse_typescript,
    ".jsx":  _parse_typescript,
    ".dart": _parse_dart,
}


def parse_file(rel_path: str, abs_path: Path) -> FileGraph | None:
    parser = _PARSERS.get(abs_path.suffix.lower())
    if not parser:
        return None
    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        return parser(rel_path, content)
    except OSError:
        return None


def checksum_only(abs_path: Path) -> str | None:
    try:
        return _checksum(abs_path.read_bytes())
    except OSError:
        return None
