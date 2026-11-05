import pytest

from grokmesh.parser import module_for_path, parse_file
from grokmesh.store import Edge, EdgeKind, Store, SymbolKind


def test_symbols_signatures_and_calls() -> None:
    result = parse_file(
        """\
def helper(x: int = 1) -> str:
    return str(x)

class Service(Base):
    async def run(self, value: int, *, flag: bool = False) -> str:
        self.prepare()
        return helper(value)

    def prepare(self):
        pass
""",
        "pkg/service.py",
        "pkg.service",
        "wip:anna",
    )
    symbols = {s.symbol_id: s for s in result.symbols}
    assert symbols["pkg.service.helper"].signature == "def helper(x: int=1) -> str"
    assert symbols["pkg.service.Service"].signature == "class Service(Base)"
    assert symbols["pkg.service.Service.run"].kind == SymbolKind.METHOD
    assert symbols["pkg.service.Service.run"].signature.startswith("async def run(")
    assert set(result.edges) == {
        Edge("pkg.service.Service.run", "pkg.service.Service.prepare", EdgeKind.CALLS, "wip:anna"),
        Edge("pkg.service.Service.run", "pkg.service.helper", EdgeKind.CALLS, "wip:anna"),
    }
    with Store() as store:
        store.replace_file("wip:anna", "pkg/service.py", result.symbols, result.edges)
        assert len(store.symbols_in_layer("wip:anna")) == 4


def test_body_hash_and_invalid_source() -> None:
    first = parse_file("def f():\n    return 1\n", "a.py", "a", "base")
    same = parse_file("def f():\n    return 1  # comment\n", "a.py", "a", "base")
    changed = parse_file("def f():\n    return 2\n", "a.py", "a", "base")
    assert first.symbols[0].body_hash == same.symbols[0].body_hash
    assert first.symbols[0].body_hash != changed.symbols[0].body_hash
    with pytest.raises(SyntaxError):
        parse_file("def f(:", "a.py", "a", "base")


def test_module_for_path() -> None:
    assert module_for_path("auth.py") == "auth"
    assert module_for_path("src/pkg/auth.py") == "pkg.auth"
    assert module_for_path("./pkg/__init__.py") == "pkg"
    with pytest.raises(ValueError):
        module_for_path("README.md")


def test_calls_resolve_through_imports() -> None:
    source = """\
from auth import hash_token
from auth import sign as auth_sign
import crypto.jwt as jwt
import os
from .util import fmt
from . import models

def login(t):
    hash_token(t)
    auth_sign(t)
    jwt.encode(t)
    os.path.join(t)
    fmt(t)
    models.User.create(t)
    unknown(t)
    login(t)
"""
    result = parse_file(source, "pkg/api.py", "pkg.api", "wip:tim")
    assert {e.dst for e in result.edges} == {
        "auth.hash_token",
        "auth.sign",
        "crypto.jwt.encode",
        "os.path.join",
        "pkg.util.fmt",
        "pkg.models.User.create",
    }


def test_class_hash_ignores_method_bodies() -> None:
    v1 = "class S:\n    x = 1\n    def run(self):\n        return 1\n"
    v2 = v1.replace("return 1", "return 2")
    v3 = v1.replace("x = 1", "x = 2")

    def hashes(src: str) -> dict[str, str]:
        return {s.symbol_id: s.body_hash for s in parse_file(src, "s.py", "s", "base").symbols}

    assert hashes(v1)["s.S"] == hashes(v2)["s.S"]
    assert hashes(v1)["s.S.run"] != hashes(v2)["s.S.run"]
    assert hashes(v1)["s.S"] != hashes(v3)["s.S"]
