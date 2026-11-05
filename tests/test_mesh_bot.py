from grokmesh.intents import close_intent, declare_intent
from grokmesh.mesh_bot import get_activity, get_collision_digest
from grokmesh.store import Lease, Store


def test_activity_excludes_expired_leases_and_closed_intents() -> None:
    with Store() as store:
        intent = declare_intent(store, "anna", "Auth", scope=["auth/**"], now=10)
        store.touch_lease(
            Lease("auth.issue", "anna", heartbeat=10, ttl_s=20, intent_id=intent.intent_id)
        )
        store.touch_lease(Lease("cli.run", "tim", heartbeat=0, ttl_s=1))
        snapshot = get_activity(store, now=20)
        assert [dev["dev_id"] for dev in snapshot["developers"]] == ["anna"]
        assert snapshot["developers"][0]["intents"][0]["scope"] == ("auth/**",)
        assert snapshot["developers"][0]["leases"][0]["expires_at"] == 30
        assert get_activity(store, "tim", now=20)["developers"] == []
        assert get_activity(store, now=30)["developers"][0]["leases"] == []
        close_intent(store, "anna", intent.intent_id, now=31)
        assert get_activity(store, now=31)["developers"] == []


def test_digest_reports_intent_conflict_and_clears_when_closed() -> None:
    with Store() as store:
        declare_intent(store, "anna", "Auth", modifies=["auth.issue"], now=10)
        other = declare_intent(store, "tim", "CLI", modifies=["auth.issue"], now=11)
        digest = get_collision_digest(store, now=20)
        assert digest["report_count"] == 2
        assert all(dev["blocked"] for dev in digest["developers"])
        assert len(get_collision_digest(store, "anna", now=20)["developers"]) == 1
        close_intent(store, "tim", other.intent_id, now=21)
        assert get_collision_digest(store, now=21)["report_count"] == 0


def test_digest_duplication_is_unconfirmed_warning() -> None:
    with Store() as store:
        declare_intent(store, "anna", "JWT token signing", produces=["auth.issue"], now=10)
        declare_intent(store, "tim", "JWT token signing", produces=["security.mint"], now=11)
        digest = get_collision_digest(store, "anna", now=20)
        assert digest["report_count"] == 1
        assert not digest["developers"][0]["blocked"]
        assert digest["developers"][0]["collisions"][0]["kind"] == "duplication"
