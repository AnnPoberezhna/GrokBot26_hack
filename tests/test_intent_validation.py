import pytest

from grokmesh.intents import declare_intent
from grokmesh.store import IntentStatus, Store


def test_declare_persists_structured_intent() -> None:
    with Store() as store:
        intent = declare_intent(
            store,
            "anna",
            "Issue JWT tokens",
            produces=["auth.issue"],
            consumes=["auth.key"],
            modifies=["auth.login"],
            scope=["auth/**"],
            now=123,
        )
        assert intent.status is IntentStatus.ACTIVE
        assert intent.created_at == 123
        assert intent.produces == ("auth.issue",)
        assert intent.consumes == ("auth.key",)
        assert intent.modifies == ("auth.login",)
        assert intent.scope == ("auth/**",)
        assert store.get_intent(intent.intent_id) == intent
        other = declare_intent(store, "anna", "Issue JWT tokens", now=124)
        assert other.intent_id != intent.intent_id


@pytest.mark.parametrize(
    "dev,goal,targets",
    [
        ("", "goal", ()),
        ("anna", "  ", ()),
        ("anna", "goal", "auth.issue"),
    ],
)
def test_invalid_intent_is_not_saved(dev: str, goal: str, targets: object) -> None:
    with Store() as store:
        with pytest.raises(ValueError):
            declare_intent(store, dev, goal, produces=targets)  # type: ignore[arg-type]
        assert store.active_intents() == []
