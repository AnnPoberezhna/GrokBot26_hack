import pytest

from grokmesh.parser import parse_file
from grokmesh.store import Edge, EdgeKind, Store, SymbolKind


def test_symbols_signatures_and_calls() -> None:
    result = parse_file('''\
def helper(x: int = 1) -> str:
    return str(x)

class Service(Base):
    async def run(self, value: int, *, flag: bool = False) -> str:
        self.prepare()
        return helper(value)

    def prepare(self):
        pass
''', "pkg/service.py", "pkg.service", "wip:anna")
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
