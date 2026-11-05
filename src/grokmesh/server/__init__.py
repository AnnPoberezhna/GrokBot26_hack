"""HTTP MCP tools backed by a caller-owned Store."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from grokmesh.collision import Collision, Severity
from grokmesh.intents import declare_intent as save_intent
from grokmesh.leases import sync_file as save_file
from grokmesh.parser import module_for_path, parse_file
from grokmesh.same_symbol import check_intent
from grokmesh.store import (
    BASE_LAYER,
    DEFAULT_LEASE_TTL_S,
    ChangeKind,
    Intent,
    Lease,
    Store,
    overlay_layer,
)


def create_server(
    store: Store,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    public_host: str | None = None,
) -> FastMCP[Any]:
    """Build tools; the caller must keep the store open while serving requests."""
    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    if public_host:
        allowed_hosts.append(public_host)
    server: FastMCP[Any] = FastMCP(
        "GrokMesh",
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
        instructions=(
            "GrokMesh keeps the coding agents of one team from colliding. "
            "Use one stable dev_id per developer. "
            "1) Before you write code, call declare_intent with the symbols you will "
            "produce or modify, as module.Class.method IDs. "
            "2) If a response has blocked=true, do not edit those symbols: show the "
            "collision message to your human and pick a listed resolution. "
            "3) After each edit, call sync_file with the full source of the changed file "
            "and your intent_id. "
            "4) Before you call another developer's function, call get_contracts for it."
        ),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=["http://localhost:*", "http://127.0.0.1:*"]
            + ([f"https://{public_host}"] if public_host else []),
        ),
    )

    def find_collisions(
        store: Store,
        dev_id: str,
        targets: list[str] | set[str],
        *,
        now: float | None = None,
    ) -> list[Collision]:
        if not dev_id.strip():
            raise ValueError("dev_id must not be blank")
        return check_intent(store, Intent("", dev_id, "", modifies=tuple(targets)), now=now)

    @server.tool()
    def check_collision(dev_id: str, symbol_ids: list[str]) -> dict[str, Any]:
        """Check target symbols against other developers' active leases."""
        collisions = find_collisions(store, dev_id, symbol_ids)
        return {
            "blocked": any(c.severity is Severity.BLOCK for c in collisions),
            "collisions": [c.to_dict() for c in collisions],
        }

    @server.tool()
    def declare_intent(
        dev_id: str,
        goal: str,
        produces: list[str] | None = None,
        consumes: list[str] | None = None,
        modifies: list[str] | None = None,
        scope: list[str] | None = None,
    ) -> dict[str, Any]:
        """Declare work and claim produced/modified symbols for 30 minutes.

        A blocked declaration writes nothing. Consumed symbols do not claim a lease.
        """
        with store.transaction():
            ts = time.time()
            targets = {s.strip() for s in (produces or []) + (modifies or []) if s.strip()}
            collisions = find_collisions(store, dev_id, targets, now=ts)
            if any(c.severity is Severity.BLOCK for c in collisions):
                return {"blocked": True, "collisions": [c.to_dict() for c in collisions]}
            intent = save_intent(
                store,
                dev_id,
                goal,
                produces=produces or [],
                consumes=consumes or [],
                modifies=modifies or [],
                scope=scope or [],
                now=ts,
            )
            for target in sorted(targets):
                base = store.get_symbol(target, BASE_LAYER)
                existing = store.get_lease(target, dev_id)
                active = existing is not None and existing.is_active(ts)
                if existing is not None and not active:
                    store.release_symbol_lease(target, dev_id)
                # A claim is not a change yet: keep the current signature as "after",
                # so collision messages and contract checks do not read it as a deletion.
                base_sig = base.signature if base else None
                store.touch_lease(
                    Lease(
                        target,
                        dev_id,
                        heartbeat=ts,
                        intent_id=intent.intent_id,
                        sig_before=base_sig,
                        sig_after=existing.sig_after if existing and active else base_sig,
                        change_kind=existing.change_kind
                        if existing and active
                        else ChangeKind.NONE,
                    )
                )
            return {
                "blocked": False,
                "intent": asdict(intent),
                "collisions": [c.to_dict() for c in collisions],
            }

    @server.tool()
    def sync_file(
        dev_id: str,
        path: str,
        source: str,
        module: str | None = None,
        intent_id: str | None = None,
        ttl_s: int = DEFAULT_LEASE_TTL_S,
    ) -> dict[str, Any]:
        """Parse uploaded Python source, publish its overlay and renew changed-symbol leases.

        path is a repository-relative label; no local files are read. module defaults
        to the module name derived from path (src/pkg/auth.py -> pkg.auth). A blocked
        sync writes nothing. Invalid Python returns a tool error without writes.
        """
        if not dev_id.strip():
            raise ValueError("dev_id must not be blank")
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        module = module or module_for_path(path)
        parsed = parse_file(source, path, module, overlay_layer(dev_id))
        with store.transaction():
            if intent_id is not None:
                intent = store.get_intent(intent_id)
                if intent is None or intent.dev_id != dev_id or intent.status != "active":
                    raise ValueError("intent_id must identify this developer's active intent")
            base = {s.symbol_id: s for s in store.symbols_in_layer(BASE_LAYER, path)}
            current = {s.symbol_id: s for s in parsed.symbols}
            targets = {
                key
                for key in base.keys() | current.keys()
                if key not in base
                or key not in current
                or (base[key].kind, base[key].signature, base[key].body_hash)
                != (current[key].kind, current[key].signature, current[key].body_hash)
            }
            ts = time.time()
            collisions = find_collisions(store, dev_id, targets, now=ts)
            if any(c.severity is Severity.BLOCK for c in collisions):
                return {"blocked": True, "collisions": [c.to_dict() for c in collisions]}
            saved = save_file(
                store,
                dev_id,
                path,
                module,
                source,
                intent_id=intent_id,
                ttl_s=ttl_s,
                now=ts,
            )
            return {
                "blocked": False,
                "symbols": [s.symbol_id for s in saved.symbols],
                "collisions": [c.to_dict() for c in collisions],
            }

    @server.tool()
    def get_contracts(symbol_ids: list[str]) -> dict[str, Any]:
        """Return base and developer signatures, owners and active lease state."""
        with store.transaction():
            ts = time.time()
            contracts = []
            for symbol_id in dict.fromkeys(symbol_ids):
                for symbol in store.symbol_layers(symbol_id):
                    owner = (
                        symbol.layer.removeprefix("wip:") if symbol.layer != BASE_LAYER else None
                    )
                    lease = store.get_lease(symbol_id, owner) if owner is not None else None
                    contracts.append(
                        {
                            "symbol_id": symbol_id,
                            "signature": symbol.signature,
                            "layer": symbol.layer,
                            "owner": owner,
                            "path": symbol.path,
                            "active": lease.is_active(ts) if lease else False,
                        }
                    )
            return {"contracts": contracts}

    return server
