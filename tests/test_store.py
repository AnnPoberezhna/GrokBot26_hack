from __future__ import annotations

from pathlib import Path

import pytest

from grokmesh.store import (
    BASE_LAYER,
    ChangeKind,
    Edge,
    EdgeKind,
    Intent,
    IntentStatus,
    Lease,
    Store,
    Symbol,
    SymbolKind,
    overlay_layer,
)

A = overlay_layer("anna")
M = overlay_layer("marcel")


def sym(symbol_id: str, layer: str, path: str = "auth.py", sig: str = "()") -> Symbol:
    return Symbol(symbol_id, layer, SymbolKind.FUNCTION, path, f"def {symbol_id}{sig}", "h")


@pytest.fixture
def store() -> Store:
    return Store()


def test_overlay_layer_rejects_empty_dev() -> None:
    assert overlay_layer("anna") == "wip:anna"
    with pytest.raises(ValueError):
        overlay_layer("")


def test_symbol_versions_per_layer(store: Store) -> None:
    store.upsert_symbol(sym("auth.hash_token", BASE_LAYER, sig="(token: str)"))
    store.upsert_symbol(sym("auth.hash_token", A, sig="(token: str, salt: bytes)"))
    layers = store.symbol_layers("auth.hash_token")
    assert [s.layer for s in layers] == [BASE_LAYER, A]
    got = store.get_symbol("auth.hash_token", A)
    assert got is not None
    assert got.signature.endswith("salt: bytes)")


def test_replace_file_swaps_symbols_and_edges(store: Store) -> None:
    store.replace_file(
        A,
        "auth.py",
        [sym("auth.issue", A), sym("auth.old", A)],
        [Edge("auth.issue", "auth.hash_token", EdgeKind.CALLS, A)],
    )
    store.replace_file(
        A,
        "auth.py",
        [sym("auth.issue", A)],
        [Edge("auth.issue", "auth.sign", EdgeKind.CALLS, A)],
    )
    assert [s.symbol_id for s in store.symbols_in_layer(A, "auth.py")] == ["auth.issue"]
    assert store.callers("auth.hash_token") == []
    assert [e.src for e in store.callers("auth.sign")] == ["auth.issue"]


def test_replace_file_rejects_foreign_symbol(store: Store) -> None:
    with pytest.raises(ValueError):
        store.replace_file(A, "auth.py", [sym("x", M)], [])
    with pytest.raises(ValueError):
        store.replace_file(A, "auth.py", [sym("x", A, path="other.py")], [])


def test_replace_file_is_atomic(store: Store) -> None:
    store.replace_file(A, "auth.py", [sym("auth.keep", A)], [])
    bad_edge = Edge("auth.x", "y", EdgeKind.CALLS, A)
    object.__setattr__(bad_edge, "kind", None)  # forces a failure inside the transaction
    with pytest.raises(AttributeError):
        store.replace_file(A, "auth.py", [sym("auth.x", A)], [bad_edge])
    assert [s.symbol_id for s in store.symbols_in_layer(A)] == ["auth.keep"]


def test_callers_span_layers(store: Store) -> None:
    store.replace_file(
        A,
        "api.py",
        [sym("api.login", A, "api.py")],
        [Edge("api.login", "auth.hash_token", EdgeKind.CALLS, A)],
    )
    store.replace_file(
        M,
        "cli.py",
        [sym("cli.main", M, "cli.py")],
        [Edge("cli.main", "auth.hash_token", EdgeKind.CALLS, M)],
    )
    assert [(e.src, e.layer) for e in store.callers("auth.hash_token")] == [
        ("api.login", A),
        ("cli.main", M),
    ]
    assert [e.dst for e in store.callees("api.login", A)] == ["auth.hash_token"]


def test_drop_layer(store: Store) -> None:
    store.replace_file(
        A, "auth.py", [sym("auth.issue", A)], [Edge("auth.issue", "x", EdgeKind.CALLS, A)]
    )
    store.upsert_symbol(sym("auth.issue", BASE_LAYER))
    store.drop_layer(A)
    assert store.symbols_in_layer(A) == []
    assert store.callers("x") == []
    assert store.get_symbol("auth.issue", BASE_LAYER) is not None


def test_intent_roundtrip_and_status(store: Store) -> None:
    saved = store.save_intent(
        Intent(
            "i1",
            "anna",
            "Issue JWT tokens",
            produces=("auth.issue_jwt",),
            modifies=("auth.hash_token",),
            scope=("auth/*",),
        ),
        now=100.0,
    )
    assert saved.created_at == 100.0
    assert saved.modifies == ("auth.hash_token",)
    store.save_intent(Intent("i2", "marcel", "CLI login"), now=101.0)

    assert [i.intent_id for i in store.active_intents()] == ["i1", "i2"]
    assert [i.intent_id for i in store.active_intents(exclude_dev="anna")] == ["i2"]

    store.set_intent_status("i1", IntentStatus.DONE, now=102.0)
    assert [i.intent_id for i in store.active_intents()] == ["i2"]
    done = store.get_intent("i1")
    assert done is not None
    assert done.created_at == 100.0
    assert done.updated_at == 102.0

    with pytest.raises(KeyError):
        store.set_intent_status("missing", IntentStatus.DONE)


def test_lease_renewal_keeps_first_signature(store: Store) -> None:
    store.touch_lease(
        Lease(
            "auth.hash_token",
            "anna",
            heartbeat=0.0,
            ttl_s=60,
            intent_id="i1",
            sig_before="(token)",
            sig_after="(token)",
        )
    )
    store.touch_lease(
        Lease(
            "auth.hash_token",
            "anna",
            heartbeat=30.0,
            ttl_s=60,
            sig_before="(token, salt)",
            sig_after="(token, salt)",
            change_kind=ChangeKind.BREAKING,
        )
    )
    lease = store.get_lease("auth.hash_token", "anna")
    assert lease is not None
    assert lease.heartbeat == 30.0
    assert lease.intent_id == "i1"
    assert lease.sig_before == "(token)"
    assert lease.sig_after == "(token, salt)"
    assert lease.change_kind is ChangeKind.BREAKING


def test_active_leases_respect_ttl_and_filters(store: Store) -> None:
    store.touch_lease(Lease("auth.hash_token", "anna", heartbeat=0.0, ttl_s=60))
    store.touch_lease(Lease("auth.hash_token", "marcel", heartbeat=50.0, ttl_s=60))
    store.touch_lease(Lease("cli.main", "marcel", heartbeat=50.0, ttl_s=60))

    assert len(store.active_leases(now=59.0)) == 3
    assert [(x.symbol_id, x.dev_id) for x in store.active_leases(now=60.0)] == [
        ("auth.hash_token", "marcel"),
        ("cli.main", "marcel"),
    ]
    only_auth = store.active_leases(["auth.hash_token"], exclude_dev="marcel", now=10.0)
    assert [x.dev_id for x in only_auth] == ["anna"]
    assert store.active_leases([], now=10.0) == []
    assert Lease("x", "d", heartbeat=0.0, ttl_s=60).is_active(59.9)
    assert not Lease("x", "d", heartbeat=0.0, ttl_s=60).is_active(60.0)


def test_release_and_expire_leases(store: Store) -> None:
    store.touch_lease(Lease("a", "anna", heartbeat=0.0, ttl_s=60, intent_id="i1"))
    store.touch_lease(Lease("b", "anna", heartbeat=0.0, ttl_s=60, intent_id="i2"))
    store.touch_lease(Lease("c", "marcel", heartbeat=0.0, ttl_s=10))
    assert store.release_leases("anna", intent_id="i1") == 1
    assert store.expire_leases(now=30.0) == 1
    assert [x.symbol_id for x in store.active_leases(now=30.0)] == ["b"]
    assert store.release_leases("anna") == 1


def test_file_store_persists(tmp_path: Path) -> None:
    db = tmp_path / "mesh.db"
    with Store(db) as s:
        s.upsert_symbol(sym("auth.issue", A))
    with Store(db) as s:
        assert s.get_symbol("auth.issue", A) is not None
