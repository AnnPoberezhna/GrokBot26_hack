from __future__ import annotations

import pytest

from grokmesh.intents import close_intent, declare_intent
from grokmesh.store import IntentStatus, Lease, Store


def test_declare_cleans_fields_and_updates_in_place() -> None:
    with Store() as store:
        first = declare_intent(
            store,
            "anna",
            "  Issue JWT tokens ",
            produces=["auth.issue_jwt", " auth.issue_jwt", ""],
            modifies=["auth.hash_token"],
            scope=["auth/*"],
            intent_id="i1",
            now=10.0,
        )
        assert first.goal == "Issue JWT tokens"
        assert first.produces == ("auth.issue_jwt",)
        assert first.status is IntentStatus.ACTIVE

        second = declare_intent(store, "anna", "Issue and refresh JWT", intent_id="i1", now=20.0)
        assert second.created_at == 10.0
        assert second.updated_at == 20.0
        assert second.produces == ()


def test_declare_generates_id_and_validates() -> None:
    with Store() as store:
        intent = declare_intent(store, "tim", "CLI login")
        assert len(intent.intent_id) == 12
        with pytest.raises(ValueError):
            declare_intent(store, "tim", "   ")
        with pytest.raises(ValueError):
            declare_intent(store, "", "x")
        with pytest.raises(PermissionError):
            declare_intent(store, "anna", "steal", intent_id=intent.intent_id)


def test_close_releases_only_that_intents_leases() -> None:
    with Store() as store:
        declare_intent(store, "anna", "JWT", intent_id="i1")
        store.touch_lease(Lease("auth.a", "anna", heartbeat=0.0, intent_id="i1"))
        store.touch_lease(Lease("auth.b", "anna", heartbeat=0.0, intent_id="i2"))
        assert close_intent(store, "anna", "i1") == 1
        closed = store.get_intent("i1")
        assert closed is not None and closed.status is IntentStatus.DONE
        assert [x.symbol_id for x in store.active_leases(now=1.0)] == ["auth.b"]
        with pytest.raises(PermissionError):
            close_intent(store, "tim", "i1")
        with pytest.raises(KeyError):
            close_intent(store, "anna", "missing")
        with pytest.raises(ValueError):
            close_intent(store, "anna", "i1", IntentStatus.ACTIVE)
