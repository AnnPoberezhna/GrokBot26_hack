"""Synchronize a developer's Python file overlay and symbol leases."""

from __future__ import annotations

import time

from grokmesh.parser import ParseResult, parse_file
from grokmesh.store import BASE_LAYER, DEFAULT_LEASE_TTL_S, ChangeKind, Lease, Store, overlay_layer


def sync_file(
    store: Store,
    dev_id: str,
    path: str,
    module: str,
    source: str,
    *,
    intent_id: str | None = None,
    ttl_s: int = DEFAULT_LEASE_TTL_S,
    now: float | None = None,
) -> ParseResult:
    """Replace a file overlay and renew leases for symbols differing from base.

    Deleted base symbols are leased too, with no after-signature. Signature
    compatibility classification is deferred to the broken-contract feature.
    """
    if ttl_s <= 0:
        raise ValueError("ttl_s must be positive")
    layer = overlay_layer(dev_id)
    parsed = parse_file(source, path, module, layer)
    ts = time.time() if now is None else now
    with store.transaction():
        base = {s.symbol_id: s for s in store.symbols_in_layer(BASE_LAYER, path)}
        previous = {s.symbol_id for s in store.symbols_in_layer(layer, path)}
        current = {s.symbol_id: s for s in parsed.symbols}
        changed = {
            key
            for key in base.keys() | current.keys()
            if key not in base
            or key not in current
            or (base[key].kind, base[key].signature, base[key].body_hash)
            != (current[key].kind, current[key].signature, current[key].body_hash)
        }
        # Keep the complete file overlay so its call graph remains available.
        store.replace_file(layer, path, parsed.symbols, parsed.edges, now=ts)
        for symbol_id in (previous | base.keys()) - changed:
            store.release_symbol_lease(symbol_id, dev_id)
        for symbol_id in changed:
            existing = store.get_lease(symbol_id, dev_id)
            if existing is not None and not existing.is_active(ts):
                store.release_symbol_lease(symbol_id, dev_id)
            before = base.get(symbol_id)
            after = current.get(symbol_id)
            store.touch_lease(
                Lease(
                    symbol_id,
                    dev_id,
                    heartbeat=ts,
                    ttl_s=ttl_s,
                    intent_id=intent_id,
                    sig_before=before.signature if before else None,
                    sig_after=after.signature if after else None,
                    change_kind=ChangeKind.ADDED if before is None else ChangeKind.NONE,
                )
            )
    return parsed
