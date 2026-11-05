from pathlib import Path

from grokmesh.collision import CollisionKind, Severity
from grokmesh.duplication import check_duplication
from grokmesh.intents import close_intent, declare_intent
from grokmesh.store import Intent, Lease, Store, Symbol, SymbolKind


def proposal(dev: str = "marcel") -> Intent:
    return Intent("new", dev, "Create JWT token signing", produces=("security.mint",))


def test_intent_match_is_warning_and_own_or_closed_work_is_excluded() -> None:
    with Store() as store:
        other = declare_intent(store, "anna", "JWT token signing", produces=["auth.issue"])
        reports = check_duplication(store, proposal())
        assert len(reports) == 1
        assert reports[0].kind is CollisionKind.DUPLICATION
        assert reports[0].severity is Severity.WARN
        assert reports[0].other_dev == "anna"
        assert reports[0].symbol_id == "auth.issue"
        assert check_duplication(store, proposal("anna")) == []
        close_intent(store, "anna", other.intent_id)
        assert check_duplication(store, proposal()) == []


def test_symbol_match_filters_expired_leases_and_tracks_replacements() -> None:
    with Store() as store:
        symbol = Symbol(
            "auth.sign_token",
            "wip:anna",
            SymbolKind.FUNCTION,
            "auth.py",
            "def sign_token(jwt: str)",
            "hash",
            summary="JWT token signing",
        )
        store.upsert_symbol(symbol)
        store.touch_lease(Lease(symbol.symbol_id, "anna", heartbeat=10, ttl_s=20))
        assert len(check_duplication(store, proposal(), now=20)) == 1
        assert check_duplication(store, proposal(), now=30) == []
        store.replace_file("wip:anna", "auth.py", [], [])
        assert check_duplication(store, proposal(), now=20) == []


def test_unrelated_work_and_query_operators_do_not_trigger_warning() -> None:
    with Store() as store:
        declare_intent(store, "anna", "Create database migration", produces=["db.migrate"])
        assert check_duplication(store, proposal()) == []
        # Prompt punctuation and FTS operators are literal text, never query syntax.
        strange = Intent("new", "marcel", '" OR * NOT : ( ) AND -')
        assert check_duplication(store, strange) == []


def test_search_tracks_intent_updates_and_deduplicates_symbol_match() -> None:
    with Store() as store:
        other = declare_intent(store, "anna", "JWT token signing", produces=["auth.issue"])
        store.upsert_symbol(
            Symbol(
                "auth.issue",
                "wip:anna",
                SymbolKind.FUNCTION,
                "auth.py",
                "def issue(jwt_token)",
                "h",
                summary="JWT token signing",
            )
        )
        store.touch_lease(Lease("auth.issue", "anna", heartbeat=10))
        reports = check_duplication(store, proposal(), now=20)
        assert len(reports) == 1
        declare_intent(store, "anna", "Database migrations", intent_id=other.intent_id)
        store.drop_layer("wip:anna")
        assert check_duplication(store, proposal(), now=20) == []


def test_existing_database_backfilled_and_reopen_does_not_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    with Store(path) as store:
        declare_intent(store, "anna", "JWT token signing", produces=["auth.issue"])
        # Simulate a pre-search database while retaining the original data.
        with store.transaction() as connection:
            for name in (
                "symbol_search_insert",
                "symbol_search_delete",
                "symbol_search_update",
                "intent_search_insert",
                "intent_search_delete",
                "intent_search_update",
            ):
                connection.execute(f"DROP TRIGGER {name}")
            connection.execute("DROP TABLE work_search")
    for _ in range(2):
        with Store(path) as store:
            assert len(check_duplication(store, proposal())) == 1
            with store.transaction() as connection:
                assert connection.execute("SELECT count(*) FROM work_search").fetchone()[0] == 1


def test_search_writes_roll_back_with_store_transaction() -> None:
    with Store() as store:
        try:
            with store.transaction():
                declare_intent(store, "anna", "JWT token signing", produces=["auth.issue"])
                raise RuntimeError("abort transaction")
        except RuntimeError:
            pass
        assert check_duplication(store, proposal()) == []
        with store.transaction() as connection:
            assert connection.execute("SELECT count(*) FROM work_search").fetchone()[0] == 0
