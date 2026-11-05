import pytest

from grokmesh.broken_contract import check_contracts, classify_change
from grokmesh.collision import CollisionKind, Severity
from grokmesh.leases import sync_file
from grokmesh.parser import parse_file
from grokmesh.store import ChangeKind, Store


@pytest.mark.parametrize(
    "before,after,kind",
    [
        (None, "def f()", ChangeKind.ADDED),
        ("def f()", None, ChangeKind.BREAKING),
        ("def f(a)", "def f(a)", ChangeKind.NONE),
        ("def f(a)", "def f(a, b=1)", ChangeKind.COMPATIBLE),
        ("def f(a)", "def f(a, *, b=1)", ChangeKind.COMPATIBLE),
        ("def f(a=1)", "def f(a=2)", ChangeKind.COMPATIBLE),
        ("def f(a)", "def f(a, b)", ChangeKind.BREAKING),
        ("def f(a)", "def f()", ChangeKind.BREAKING),
        ("def f(a)", "def f(b)", ChangeKind.BREAKING),
        ("def f(a=1)", "def f(a)", ChangeKind.BREAKING),
        ("def f(a)", "def f(a, /)", ChangeKind.BREAKING),
        ("def f(a, /)", "def f(a)", ChangeKind.COMPATIBLE),
        ("def f(*, a=1)", "def f(*, a)", ChangeKind.BREAKING),
        ("def f(*, a)", "def f()", ChangeKind.BREAKING),
        ("def f()", "def f(*, a)", ChangeKind.BREAKING),
        ("def f(*args)", "def f()", ChangeKind.BREAKING),
        ("def f(**kwargs)", "def f()", ChangeKind.BREAKING),
        ("def f(*args)", "def f(a=1, *args)", ChangeKind.BREAKING),
        ("def f(a: str)", "def f(a: bytes)", ChangeKind.BREAKING),
        ("def f() -> str", "def f() -> bytes", ChangeKind.BREAKING),
        ("def f()", "async def f()", ChangeKind.BREAKING),
        ("class A(Base)", "class A(Other)", ChangeKind.BREAKING),
    ],
)
def test_classify_signatures(before: str | None, after: str | None, kind: ChangeKind) -> None:
    assert classify_change(before, after) is kind


def base_file(store: Store, path: str, module: str, source: str) -> None:
    parsed = parse_file(source, path, module, "base")
    store.replace_file("base", path, parsed.symbols, parsed.edges)


def test_breaking_change_names_caller_and_respects_ttl() -> None:
    with Store() as store:
        base_file(store, "auth.py", "auth", "def issue(token):\n    return token\n")
        base_file(
            store, "api.py", "api", "from auth import issue\ndef login():\n    return issue('a')\n"
        )
        sync_file(
            store,
            "marcel",
            "api.py",
            "api",
            "from auth import issue\ndef login():\n    return issue('b')\n",
            now=10,
            ttl_s=60,
        )
        sync_file(
            store,
            "anna",
            "auth.py",
            "auth",
            "def issue(token, salt):\n    return token\n",
            now=20,
            ttl_s=60,
        )
        reports = check_contracts(store, "marcel", ["api.login"], now=30)
        assert len(reports) == 1
        assert reports[0].severity is Severity.BLOCK
        assert reports[0].kind is CollisionKind.BROKEN_CONTRACT
        assert reports[0].caller_symbol_id == "api.login"
        assert reports[0].other_dev == "anna"
        assert reports[0].sig_after == "def issue(token, salt)"
        provider = check_contracts(store, "anna", now=30)
        assert len(provider) == 1 and provider[0].severity is Severity.WARN
        assert check_contracts(store, "unrelated", now=30) == []
        assert check_contracts(store, "marcel", ["other.func"], now=30) == []
        assert check_contracts(store, "marcel", now=80) == []
        assert check_contracts(store, "anna", now=70) == []


def test_optional_parameter_and_same_developer_do_not_collide() -> None:
    with Store() as store:
        base_file(store, "auth.py", "auth", "def issue(token):\n    return token\n")
        sync_file(
            store,
            "marcel",
            "api.py",
            "api",
            "from auth import issue\ndef login():\n    return issue('a')\n",
            now=10,
        )
        sync_file(
            store,
            "anna",
            "auth.py",
            "auth",
            "def issue(token, salt=None):\n    return token\n",
            now=20,
        )
        lease = store.get_lease("auth.issue", "anna")
        assert lease is not None and lease.change_kind is ChangeKind.COMPATIBLE
        assert check_contracts(store, "marcel", now=30) == []
        # No leased foreign caller: a base edge alone cannot create an impact.
        store.release_leases("marcel")
        sync_file(
            store, "anna", "auth.py", "auth", "def issue(token, salt):\n    return token\n", now=40
        )
        assert check_contracts(store, "anna", now=50) == []


def test_planned_edit_of_a_main_caller_sees_the_breaking_change() -> None:
    with Store() as store:
        base_file(store, "auth.py", "auth", "def issue(token):\n    return token\n")
        base_file(
            store, "api.py", "api", "from auth import issue\ndef login():\n    return issue('a')\n"
        )
        sync_file(
            store, "anna", "auth.py", "auth", "def issue(token, ttl):\n    return token\n", now=1
        )
        # Marcel has no overlay yet: main's login() calls the changed issue().
        [report] = check_contracts(store, "marcel", ["api.login"], now=2)
        assert report.severity is Severity.BLOCK
        assert report.caller_symbol_id == "api.login"
        assert report.message.startswith("CONFLICT: api.login (marcel) calls auth.issue (anna)")
        # Without an explicit target, a base edge alone creates no impact.
        assert check_contracts(store, "marcel", now=2) == []
        assert check_contracts(store, "anna", now=2) == []
        # Marcel's overlay of login() no longer calls issue(): the overlay replaces main.
        sync_file(store, "marcel", "api.py", "api", "def login():\n    return 'x'\n", now=3)
        assert check_contracts(store, "marcel", ["api.login"], now=4) == []
