"""Same-symbol collision: an intent or sync against another developer's active work.

Stage 1 of the detection cascade. It is deterministic and needs no LLM, so the
pre-edit check can block an edit.

Rules:
- Another developer holds an active lease on the same symbol -> BLOCK.
- Another developer holds an active lease on a containing or contained symbol
  (``auth.S`` and ``auth.S.run``) -> WARN.
- Another developer's active intent produces or modifies the same symbol -> BLOCK.
  This catches the collision before anyone writes code.
"""

from __future__ import annotations

import time
from collections.abc import Iterable

from grokmesh.collision import (
    Collision,
    CollisionKind,
    Resolution,
    Severity,
    format_age,
    symbols_overlap,
)
from grokmesh.store import Intent, Lease, Store

_LEASE_RESOLUTIONS = (Resolution.REUSE, Resolution.CODE_AGAINST_STUB, Resolution.NEGOTIATE)
_INTENT_RESOLUTIONS = (Resolution.CODE_AGAINST_STUB, Resolution.NEGOTIATE, Resolution.ESCALATE)


def _lease_collision(target: str, lease: Lease, goal: str | None, now: float) -> Collision:
    exact = lease.symbol_id == target
    age = now - lease.heartbeat
    lines = [
        f"{'CONFLICT' if exact else 'WARNING'}: {lease.symbol_id} is active "
        f"({lease.dev_id}, {format_age(age)})."
    ]
    if not exact:
        lines.append(f"It overlaps with {target}.")
    if lease.sig_before != lease.sig_after:
        lines.append(f"Change: {lease.sig_before or '(new)'} -> {lease.sig_after or '(deleted)'}")
    if goal:
        lines.append(f'Intent: "{goal}".')
    return Collision(
        kind=CollisionKind.SAME_SYMBOL,
        severity=Severity.BLOCK if exact else Severity.WARN,
        symbol_id=lease.symbol_id,
        other_dev=lease.dev_id,
        message="\n".join(lines),
        other_intent_id=lease.intent_id,
        other_goal=goal,
        sig_before=lease.sig_before,
        sig_after=lease.sig_after,
        age_s=age,
        resolutions=_LEASE_RESOLUTIONS,
    )


def check_symbols(
    store: Store, dev_id: str, symbol_ids: Iterable[str], *, now: float | None = None
) -> list[Collision]:
    """Check symbols that ``dev_id`` is about to edit against other developers' leases."""
    ts = time.time() if now is None else now
    targets = list(dict.fromkeys(symbol_ids))
    if not targets:
        return []
    goals: dict[str, str | None] = {}
    found: dict[tuple[str, str], Collision] = {}
    for lease in store.active_leases(exclude_dev=dev_id, now=ts):
        for target in targets:
            if not symbols_overlap(target, lease.symbol_id):
                continue
            if lease.intent_id and lease.intent_id not in goals:
                intent = store.get_intent(lease.intent_id)
                goals[lease.intent_id] = intent.goal if intent else None
            goal = goals.get(lease.intent_id) if lease.intent_id else None
            c = _lease_collision(target, lease, goal, ts)
            key = (lease.symbol_id, lease.dev_id)
            if key not in found or c.severity is Severity.BLOCK:
                found[key] = c
    return _sorted(found.values())


def check_intent(store: Store, intent: Intent, *, now: float | None = None) -> list[Collision]:
    """Check a declared intent against other developers' leases and active intents."""
    ts = time.time() if now is None else now
    targets = [*intent.produces, *intent.modifies]
    found: dict[tuple[str, str], Collision] = {
        (c.symbol_id, c.other_dev): c for c in check_symbols(store, intent.dev_id, targets, now=ts)
    }
    for other in store.active_intents(exclude_dev=intent.dev_id):
        for symbol in (*other.produces, *other.modifies):
            if symbol not in targets or (symbol, other.dev_id) in found:
                continue
            found[(symbol, other.dev_id)] = Collision(
                kind=CollisionKind.SAME_SYMBOL,
                severity=Severity.BLOCK,
                symbol_id=symbol,
                other_dev=other.dev_id,
                message=(
                    f"CONFLICT: {other.dev_id} plans to change {symbol}.\n"
                    f'Intent: "{other.goal}" ({format_age(ts - other.created_at)}).'
                ),
                other_intent_id=other.intent_id,
                other_goal=other.goal,
                age_s=ts - other.created_at,
                resolutions=_INTENT_RESOLUTIONS,
            )
    return _sorted(found.values())


def check_dev(store: Store, dev_id: str, *, now: float | None = None) -> list[Collision]:
    """Return every same-symbol collision that touches the work of ``dev_id``."""
    ts = time.time() if now is None else now
    leased = [x.symbol_id for x in store.active_leases(now=ts) if x.dev_id == dev_id]
    found = {(c.symbol_id, c.other_dev): c for c in check_symbols(store, dev_id, leased, now=ts)}
    for intent in store.active_intents():
        if intent.dev_id != dev_id:
            continue
        for c in check_intent(store, intent, now=ts):
            key = (c.symbol_id, c.other_dev)
            if key not in found or c.severity is Severity.BLOCK:
                found[key] = c
    return _sorted(found.values())


def _sorted(collisions: Iterable[Collision]) -> list[Collision]:
    order = {Severity.BLOCK: 0, Severity.WARN: 1}
    return sorted(collisions, key=lambda c: (order[c.severity], c.symbol_id, c.other_dev))
