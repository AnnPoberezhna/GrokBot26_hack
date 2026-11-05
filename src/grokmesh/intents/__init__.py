"""Intents: structured task statements linked to symbols."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable

from grokmesh.store import Intent, IntentStatus, Store


def _clean(values: Iterable[str]) -> tuple[str, ...]:
    """Strip, drop empty values and duplicates, keep the first-seen order."""
    if isinstance(values, (str, bytes)):
        raise ValueError("symbol and scope fields must be sequences of strings")
    items = tuple(values)
    if any(not isinstance(value, str) for value in items):
        raise ValueError("symbol and scope fields must contain strings")
    return tuple(dict.fromkeys(v.strip() for v in items if v and v.strip()))


def declare_intent(
    store: Store,
    dev_id: str,
    goal: str,
    *,
    produces: Iterable[str] = (),
    consumes: Iterable[str] = (),
    modifies: Iterable[str] = (),
    scope: Iterable[str] = (),
    intent_id: str | None = None,
    now: float | None = None,
) -> Intent:
    """Store a new active intent, or update an existing one with the same ID.

    ``produces``: symbols the work will create, e.g. ``auth.issue_jwt``.
    ``consumes``: symbols the work will call but not change.
    ``modifies``: existing symbols the work will change.
    ``scope``: path globs the work stays inside, e.g. ``auth/*``.
    """
    if not dev_id.strip():
        raise ValueError("dev_id must not be empty")
    if not goal.strip():
        raise ValueError("goal must not be empty")
    iid = intent_id or uuid.uuid4().hex[:12]
    existing = store.get_intent(iid)
    if existing is not None and existing.dev_id != dev_id:
        raise PermissionError(f"intent {iid} belongs to {existing.dev_id}")
    ts = time.time() if now is None else now
    return store.save_intent(
        Intent(
            intent_id=iid,
            dev_id=dev_id,
            goal=goal.strip(),
            produces=_clean(produces),
            consumes=_clean(consumes),
            modifies=_clean(modifies),
            scope=_clean(scope),
            status=IntentStatus.ACTIVE,
            created_at=existing.created_at if existing else ts,
        ),
        now=ts,
    )


def close_intent(
    store: Store,
    dev_id: str,
    intent_id: str,
    status: IntentStatus = IntentStatus.DONE,
    *,
    now: float | None = None,
) -> int:
    """Close an intent and release its leases. Return the number of released leases."""
    if status is IntentStatus.ACTIVE:
        raise ValueError("close_intent needs a final status")
    intent = store.get_intent(intent_id)
    if intent is None:
        raise KeyError(intent_id)
    if intent.dev_id != dev_id:
        raise PermissionError(f"intent {intent_id} belongs to {intent.dev_id}")
    with store.transaction():
        store.set_intent_status(intent_id, status, now=now)
        return store.release_leases(dev_id, intent_id=intent_id)
