from pathlib import Path

import pytest

from grokmesh.leases import index_base, sync_file
from grokmesh.parser import parse_file
from grokmesh.store import ChangeKind, Store


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


def test_base_index_prevents_false_leases_in_shared_file(tmp_path: Path) -> None:
    src = "def a():\n    return 1\n\n\ndef b():\n    return 1\n"
    (tmp_path / "m.py").write_text(src)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("def z(): pass\n")
    (tmp_path / "broken.py").write_text("def f(:\n")
    with Store() as store:
        report = index_base(store, tmp_path)
        assert report.indexed == ["m.py"]
        assert list(report.skipped) == ["broken.py"]

        sync_file(
            store,
            "anna",
            "m.py",
            "m",
            src.replace("return 1\n\n\ndef b", "return 9\n\n\ndef b"),
            now=1,
        )
        sync_file(
            store,
            "tim",
            "m.py",
            "m",
            src.replace("return 1\n", "return 7\n").replace(
                "return 7\n\n\ndef b", "return 1\n\n\ndef b"
            ),
            now=1,
        )
        leases = {(x.symbol_id, x.dev_id) for x in store.active_leases(now=1)}
        assert leases == {("m.a", "anna"), ("m.b", "tim")}


def test_deleted_symbol_is_breaking() -> None:
    with Store() as store:
        base = parse_file("def f():\n    pass\n", "a.py", "a", "base")
        store.replace_file("base", "a.py", base.symbols, base.edges)
        sync_file(store, "anna", "a.py", "a", "", now=1)
        lease = store.get_lease("a.f", "anna")
        assert lease is not None and lease.change_kind is ChangeKind.BREAKING


def test_index_base_drops_removed_files(tmp_path: Path) -> None:
    (tmp_path / "old.py").write_text("def f():\n    pass\n")
    with Store() as store:
        index_base(store, tmp_path)
        (tmp_path / "old.py").unlink()
        index_base(store, tmp_path)
        assert store.symbols_in_layer("base") == []
