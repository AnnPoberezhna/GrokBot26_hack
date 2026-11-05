"""Read-only team activity and collision summaries for a shared Mesh Bot."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from grokmesh.broken_contract import check_contracts
from grokmesh.collision import Collision, Severity
from grokmesh.duplication import check_duplication
from grokmesh.same_symbol import check_dev
from grokmesh.store import Store, overlay_layer


def get_activity(
    store: Store,
    dev_id: str | None = None,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """Snapshot active intents and unexpired leases, optionally for one developer."""
    if dev_id is not None and not dev_id.strip():
        raise ValueError("dev_id must not be blank")
    ts = time.time() if now is None else now
    with store.transaction():
        intents = store.active_intents()
        leases = store.active_leases(now=ts)
        owners = sorted({i.dev_id for i in intents} | {lease.dev_id for lease in leases})
        developers = []
        for owner in owners:
            if dev_id is not None and owner != dev_id:
                continue
            claims = []
            for lease in leases:
                if lease.dev_id != owner:
                    continue
                symbol = store.get_symbol(lease.symbol_id, overlay_layer(owner))
                claims.append(
                    {
                        **asdict(lease),
                        "path": symbol.path if symbol else None,
                        "expires_at": lease.heartbeat + lease.ttl_s,
                    }
                )
            developers.append(
                {
                    "dev_id": owner,
                    "intents": [asdict(i) for i in intents if i.dev_id == owner],
                    "leases": claims,
                }
            )
        return {"generated_at": ts, "developers": developers}


def get_collision_digest(
    store: Store,
    dev_id: str | None = None,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """Read current collisions grouped by affected developer; never post messages.

    Reports are per developer's perspective, so a shared conflict can appear in
    two groups. Duplication matches remain unconfirmed and cannot block work.
    """
    if dev_id is not None and not dev_id.strip():
        raise ValueError("dev_id must not be blank")
    ts = time.time() if now is None else now
    with store.transaction():
        intents = store.active_intents()
        leases = store.active_leases(now=ts)
        owners = sorted({i.dev_id for i in intents} | {lease.dev_id for lease in leases})
        developers = []
        report_count = 0
        for owner in owners:
            if dev_id is not None and owner != dev_id:
                continue
            reports = check_dev(store, owner, now=ts) + check_contracts(store, owner, now=ts)
            for intent in intents:
                if intent.dev_id == owner:
                    reports += check_duplication(store, intent, now=ts)
            unique: dict[tuple[str, str, str, str | None], Collision] = {}
            for report in reports:
                key = (report.kind, report.symbol_id, report.other_dev, report.caller_symbol_id)
                if key not in unique or report.severity is Severity.BLOCK:
                    unique[key] = report
            ordered = sorted(
                unique.values(),
                key=lambda r: (
                    r.severity is not Severity.BLOCK,
                    r.kind,
                    r.symbol_id,
                    r.other_dev,
                    r.caller_symbol_id or "",
                ),
            )
            if ordered:
                developers.append(
                    {
                        "dev_id": owner,
                        "blocked": any(r.severity is Severity.BLOCK for r in ordered),
                        "collisions": [r.to_dict() for r in ordered],
                    }
                )
                report_count += len(ordered)
        return {"generated_at": ts, "developers": developers, "report_count": report_count}
