from __future__ import annotations

from grokmesh.collision import CollisionKind, Resolution, Severity, symbols_overlap
from grokmesh.intents import declare_intent
from grokmesh.leases import sync_file
from grokmesh.parser import parse_file
from grokmesh.same_symbol import check_dev, check_intent, check_symbols
from grokmesh.store import Lease, Store

AUTH = "def hash_token(token: str) -> str:\n    return token\n\n\ndef sign(t):\n    return t\n"


def seeded() -> Store:
    store = Store()
    base = parse_file(AUTH, "auth.py", "auth", "base")
    store.replace_file("base", "auth.py", base.symbols, base.edges)
    return store


def test_symbols_overlap() -> None:
    assert symbols_overlap("a.S", "a.S")
    assert symbols_overlap("a.S", "a.S.run")
    assert symbols_overlap("a.S.run", "a.S")
    assert not symbols_overlap("a.S", "a.Service")


def test_sync_lease_blocks_other_dev_on_same_symbol() -> None:
    with seeded() as store:
        intent = declare_intent(store, "anna", "JWT issuance", intent_id="i1", now=0.0)
        changed = AUTH.replace("hash_token(token: str)", "hash_token(token: str, salt: bytes)")
        sync_file(store, "anna", "auth.py", "auth", changed, intent_id=intent.intent_id, now=0.0)

        [c] = check_symbols(store, "tim", ["auth.hash_token"], now=240.0)
        assert c.kind is CollisionKind.SAME_SYMBOL
        assert c.severity is Severity.BLOCK
        assert c.other_dev == "anna"
        assert c.other_goal == "JWT issuance"
        assert c.sig_after == "def hash_token(token: str, salt: bytes) -> str"
        assert "CONFLICT: auth.hash_token is active (anna, 4 min ago)." in c.message
        assert Resolution.CODE_AGAINST_STUB in c.resolutions
        assert c.to_dict()["severity"] == "block"

        assert check_symbols(store, "anna", ["auth.hash_token"], now=240.0) == []
        assert check_symbols(store, "tim", ["auth.sign"], now=240.0) == []


def test_lease_expiry_clears_collision() -> None:
    with Store() as store:
        store.touch_lease(Lease("auth.f", "anna", heartbeat=0.0, ttl_s=60))
        assert check_symbols(store, "tim", ["auth.f"], now=59.0)
        assert check_symbols(store, "tim", ["auth.f"], now=60.0) == []


def test_containing_symbol_warns() -> None:
    with Store() as store:
        store.touch_lease(Lease("svc.S.run", "anna", heartbeat=0.0))
        [c] = check_symbols(store, "tim", ["svc.S"], now=1.0)
        assert c.severity is Severity.WARN
        assert c.symbol_id == "svc.S.run"


def test_intent_vs_intent_before_any_code() -> None:
    with Store() as store:
        declare_intent(store, "anna", "JWT issuance", modifies=["auth.hash_token"], now=0.0)
        mine = declare_intent(
            store, "tim", "Token hashing util", produces=["auth.hash_token"], now=30.0
        )
        [c] = check_intent(store, mine, now=30.0)
        assert c.severity is Severity.BLOCK
        assert c.other_dev == "anna"
        assert c.other_goal == "JWT issuance"
        assert "anna plans to change auth.hash_token" in c.message


def test_lease_wins_over_intent_and_check_dev_merges() -> None:
    with Store() as store:
        declare_intent(store, "anna", "JWT", modifies=["auth.f"], intent_id="i1", now=0.0)
        store.touch_lease(Lease("auth.f", "anna", heartbeat=0.0, intent_id="i1"))
        store.touch_lease(Lease("auth.g", "anna", heartbeat=0.0))
        declare_intent(store, "tim", "Refactor", modifies=["auth.f"], now=1.0)
        store.touch_lease(Lease("auth.g", "tim", heartbeat=1.0))

        found = check_dev(store, "tim", now=2.0)
        assert [(c.symbol_id, c.other_dev) for c in found] == [
            ("auth.f", "anna"),
            ("auth.g", "anna"),
        ]
        assert found[0].age_s == 2.0  # from the lease, not the intent
        assert check_dev(store, "nobody", now=2.0) == []
