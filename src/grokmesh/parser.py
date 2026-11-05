"""Extract Python symbols and conservatively resolved calls from one source file.

Module names are supplied by the caller (for example, ``pkg.auth``). Calls are
resolved only to top-level definitions by name, or to methods via ``self`` or
``cls`` in the same class. Imports, aliases, dynamic dispatch and name
shadowing are not resolved; call edges are therefore best-effort, not proof.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass

from grokmesh.store import Edge, EdgeKind, Symbol, SymbolKind


@dataclass(frozen=True, slots=True)
class ParseResult:
    symbols: list[Symbol]
    edges: list[Edge]


def parse_file(source: str, path: str, module: str, layer: str) -> ParseResult:
    """Parse source without writing to the store; invalid syntax raises SyntaxError."""
    if not module:
        raise ValueError("module must not be empty")
    tree = ast.parse(source, filename=path)
    symbols: list[Symbol] = []
    edges: list[Edge] = []
    top_names = {
        n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }

    def visit_definition(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
                         parents: tuple[str, ...], in_class: bool) -> None:
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
        body = ast.dump(ast.Module(body=node.body, type_ignores=[]), include_attributes=False)
        symbols.append(Symbol(symbol_id, layer, kind, path, signature,
                              hashlib.sha256(body.encode()).hexdigest()))

        class Calls(ast.NodeVisitor):
            def visit_Call(self, call: ast.Call) -> None:
                target = call.func
                dst = None
                if isinstance(target, ast.Name) and target.id in top_names:
                    dst = f"{module}.{target.id}"
                elif (in_class and isinstance(target, ast.Attribute)
                      and isinstance(target.value, ast.Name)
                      and target.value.id in {"self", "cls"}):
                    dst = ".".join((module, *parents, target.attr))
                if dst is not None:
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
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit_definition(statement, (*parents, node.name), isinstance(node, ast.ClassDef))

    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            visit_definition(item, (), False)
    return ParseResult(symbols, list(dict.fromkeys(edges)))
