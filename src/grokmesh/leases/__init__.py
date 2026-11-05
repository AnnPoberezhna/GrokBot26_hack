"""Synchronize a developer's Python file overlay and symbol leases."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from grokmesh.parser import ParseResult, module_for_path, parse_file
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

    Deleted base symbols are leased too, with no after-signature, and count as
    breaking. Signature compatibility classification of edited symbols is
    deferred to the broken-contract feature.
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
                    change_kind=_change_kind(before is not None, after is not None),
                )
            )
    return parsed


def _change_kind(in_base: bool, in_overlay: bool) -> ChangeKind:
    if not in_base:
        return ChangeKind.ADDED
    if not in_overlay:
        return ChangeKind.BREAKING
    return ChangeKind.NONE


_SKIP_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}
)


@dataclass(frozen=True, slots=True)
class IndexReport:
    indexed: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)


def index_base(store: Store, root: str | Path) -> IndexReport:
    """Rebuild the base layer from every Python file under ``root``.

    Run this on a checkout of the main branch. Without a base layer, every
    symbol in a synced file looks new, and two developers who edit different
    functions of one file collide on all of them.
    """
    root = Path(root)
    report = IndexReport()
    with store.transaction():
        store.drop_layer(BASE_LAYER)
        for file in sorted(root.rglob("*.py")):
            rel = file.relative_to(root)
            if any(part in _SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
                continue
            path = rel.as_posix()
            try:
                parsed = parse_file(
                    file.read_text(encoding="utf-8"), path, module_for_path(path), BASE_LAYER
                )
            except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                report.skipped[path] = f"{type(exc).__name__}: {exc}"
                continue
            store.replace_file(BASE_LAYER, path, parsed.symbols, parsed.edges)
            report.indexed.append(path)
    return report
