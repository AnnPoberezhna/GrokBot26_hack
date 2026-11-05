import pytest

from grokmesh.leases import sync_file
from grokmesh.parser import parse_file
from grokmesh.store import Store


def test_sync_renews_changed_and_deleted_symbols_and_releases_reverted() -> None:
    with Store() as store:
        source = "def keep():\n    return 1\ndef gone():\n    pass\n"
        base = parse_file(source, "a.py", "a", "base")
        store.replace_file("base", "a.py", base.symbols, base.edges)
        sync_file(store, "anna", "a.py", "a", "def keep():\n    return 2\n", now=10, ttl_s=20)
        assert [x.symbol_id for x in store.active_leases(now=10)] == ["a.gone", "a.keep"]
        gone = store.get_lease("a.gone", "anna")
        assert gone is not None and gone.sig_after is None
        sync_file(store, "anna", "a.py", "a", "def keep():\n    return 3\n", now=20, ttl_s=20)
        keep = store.get_lease("a.keep", "anna")
        assert keep is not None and keep.heartbeat == 20
        assert len(store.active_leases(now=39)) == 2
        assert store.active_leases(now=40) == []
        sync_file(store, "anna", "a.py", "a", source, now=41)
        assert store.active_leases(now=41) == []


def test_invalid_sync_leaves_overlay_and_leases_intact() -> None:
    with Store() as store:
        sync_file(store, "anna", "a.py", "a", "def f():\n    pass\n", now=10)
        with pytest.raises(SyntaxError):
            sync_file(store, "anna", "a.py", "a", "def f(:", now=20)
        assert store.get_symbol("a.f", "wip:anna") is not None
        lease = store.get_lease("a.f", "anna")
        assert lease is not None and lease.heartbeat == 10
