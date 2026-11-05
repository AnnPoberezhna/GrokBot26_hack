"""Extract Python symbols and conservatively resolved calls from one source file.

Module names come from the caller (for example, ``pkg.auth``) or from
``module_for_path``. The parser resolves calls to:

- top-level definitions of the same file, by name,
- methods of the same class, through ``self`` or ``cls``,
- imported names: ``from x import f as g`` then ``g()``, and
  ``import x.y as z`` then ``z.f()``, including relative imports.

Dynamic dispatch and name shadowing are not resolved. Call edges are
best-effort, not proof.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath

from grokmesh.store import Edge, EdgeKind, Symbol, SymbolKind

_DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_SOURCE_ROOTS = ("src",)


@dataclass(frozen=True, slots=True)
class ParseResult:
    symbols: list[Symbol]
    edges: list[Edge]


def module_for_path(path: str, source_roots: tuple[str, ...] = _SOURCE_ROOTS) -> str:
    """Map a repository-relative file path to its module name.

    ``src/pkg/auth.py`` -> ``pkg.auth``; ``pkg/__init__.py`` -> ``pkg``.
    """
    parts = list(PurePosixPath(path.replace("\\", "/")).parts)
    if parts and parts[0] in (".", "/"):
        parts = parts[1:]
    if not parts or not parts[-1].endswith(".py"):
        raise ValueError(f"not a Python file: {path!r}")
    if len(parts) > 1 and parts[0] in source_roots:
        parts = parts[1:]
    parts[-1] = parts[-1].removesuffix(".py")
    if parts[-1] == "__init__" and len(parts) > 1:
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_relative(module: str, level: int, target: str | None) -> str | None:
    if level == 0:
        return target
    package = module.split(".")[:-level]
    if not package and level > 0:
        # Relative import above the top-level package: cannot resolve.
        return None
    return ".".join([*package, *([target] if target else [])])


def _import_aliases(tree: ast.Module, module: str) -> dict[str, str]:
    """Map each local name bound by an import to the fully qualified name it refers to."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    head = a.name.split(".")[0]
                    aliases[head] = head
        elif isinstance(node, ast.ImportFrom):
            source = _resolve_relative(module, node.level, node.module)
            if source is None:
                continue
            for a in node.names:
                if a.name == "*":
                    continue
                aliases[a.asname or a.name] = f"{source}.{a.name}"
    return aliases


def _dotted(expr: ast.expr) -> list[str] | None:
    """Return ``["a", "b", "c"]`` for ``a.b.c``, or None for any other expression."""
    parts: list[str] = []
    while isinstance(expr, ast.Attribute):
        parts.append(expr.attr)
        expr = expr.value
    if not isinstance(expr, ast.Name):
        return None
    parts.append(expr.id)
    return parts[::-1]


def _own_body(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[ast.stmt]:
    """Return the statements that belong to this symbol's own hash.

    A class hash excludes its methods and nested classes. They are separate
    symbols, so an edit to one method must not change the class.
    """
    if isinstance(node, ast.ClassDef):
        return [s for s in node.body if not isinstance(s, _DEFINITIONS)]
    return node.body


def parse_file(source: str, path: str, module: str, layer: str) -> ParseResult:
    """Parse source without writing to the store; invalid syntax raises SyntaxError."""
    if not module:
        raise ValueError("module must not be empty")
    tree = ast.parse(source, filename=path)
    symbols: list[Symbol] = []
    edges: list[Edge] = []
    top_names = {n.name for n in tree.body if isinstance(n, _DEFINITIONS)}
    imports = _import_aliases(tree, module)

    def resolve(target: ast.expr, parents: tuple[str, ...], in_class: bool) -> str | None:
        parts = _dotted(target)
        if parts is None:
            return None
        head, rest = parts[0], parts[1:]
        if in_class and head in {"self", "cls"} and len(rest) == 1:
            return ".".join((module, *parents, rest[0]))
        if head in top_names:
            return ".".join((module, head, *rest))
        if head in imports:
            return ".".join((imports[head], *rest))
        return None

    def visit_definition(
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        parents: tuple[str, ...],
        in_class: bool,
    ) -> None:
        symbol_id = ".".join((module, *parents, node.name))
        if isinstance(node, ast.ClassDef):
            kind = SymbolKind.CLASS
            bases = [ast.unparse(b) for b in node.bases]
            bases.extend(ast.unparse(k) for k in node.keywords)
            signature = f"class {node.name}" + (f"({', '.join(bases)})" if bases else "")
        else:
            kind = SymbolKind.METHOD if in_class else SymbolKind.FUNCTION
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            signature = f"{prefix} {node.name}({ast.unparse(node.args)})"
            if node.returns is not None:
                signature += f" -> {ast.unparse(node.returns)}"
        body = ast.dump(ast.Module(body=_own_body(node), type_ignores=[]), include_attributes=False)
        symbols.append(
            Symbol(
                symbol_id, layer, kind, path, signature, hashlib.sha256(body.encode()).hexdigest()
            )
        )

        class Calls(ast.NodeVisitor):
            def visit_Call(self, call: ast.Call) -> None:
                dst = resolve(call.func, parents, in_class)
                if dst is not None and dst != symbol_id:
                    edges.append(Edge(symbol_id, dst, EdgeKind.CALLS, layer))
                self.generic_visit(call)

            def visit_FunctionDef(self, nested: ast.FunctionDef) -> None:
                pass

            def visit_AsyncFunctionDef(self, nested: ast.AsyncFunctionDef) -> None:
                pass

            def visit_ClassDef(self, nested: ast.ClassDef) -> None:
                pass

        calls = Calls()
        for statement in node.body:
            calls.visit(statement)
            if isinstance(statement, _DEFINITIONS):
                visit_definition(statement, (*parents, node.name), isinstance(node, ast.ClassDef))

    for item in tree.body:
        if isinstance(item, _DEFINITIONS):
            visit_definition(item, (), False)
    return ParseResult(symbols, list(dict.fromkeys(edges)))
