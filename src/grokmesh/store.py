"""SQLite store: symbols per layer, edges, intents and leases.

Layers:
- ``base`` holds the index of the main branch.
- ``wip:<dev_id>`` holds one developer's uncommitted symbols (the overlay).

A lease is active while ``now - heartbeat < ttl_s``. Nobody clears leases by hand.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

BASE_LAYER = "base"
DEFAULT_LEASE_TTL_S = 1800

SCHEMA = """
CREATE TABLE IF NOT EXISTS symbol (
    symbol_id  TEXT NOT NULL,
    layer      TEXT NOT NULL,
    kind       TEXT NOT NULL,
    path       TEXT NOT NULL,
    signature  TEXT NOT NULL,
    body_hash  TEXT NOT NULL,
    summary    TEXT,
    updated_at REAL NOT NULL,
    PRIMARY KEY (symbol_id, layer)
);
CREATE INDEX IF NOT EXISTS symbol_layer_path ON symbol (layer, path);

CREATE TABLE IF NOT EXISTS edge (
    src   TEXT NOT NULL,
    dst   TEXT NOT NULL,
    kind  TEXT NOT NULL,
    layer TEXT NOT NULL,
    PRIMARY KEY (src, dst, kind, layer)
);
CREATE INDEX IF NOT EXISTS edge_dst ON edge (dst, kind);

CREATE TABLE IF NOT EXISTS intent (
    intent_id  TEXT PRIMARY KEY,
    dev_id     TEXT NOT NULL,
    goal       TEXT NOT NULL,
    produces   TEXT NOT NULL,
    consumes   TEXT NOT NULL,
    modifies   TEXT NOT NULL,
    scope      TEXT NOT NULL,
    status     TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS intent_status ON intent (status, dev_id);

CREATE TABLE IF NOT EXISTS lease (
    symbol_id   TEXT NOT NULL,
    dev_id      TEXT NOT NULL,
    intent_id   TEXT,
    heartbeat   REAL NOT NULL,
    ttl_s       INTEGER NOT NULL,
    sig_before  TEXT,
    sig_after   TEXT,
    change_kind TEXT NOT NULL,
    PRIMARY KEY (symbol_id, dev_id)
);
CREATE INDEX IF NOT EXISTS lease_dev ON lease (dev_id);
"""


def overlay_layer(dev_id: str) -> str:
    """Return the layer name of one developer's uncommitted work."""
    if not dev_id:
        raise ValueError("dev_id must not be empty")
    return f"wip:{dev_id}"


class SymbolKind(StrEnum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ENDPOINT = "endpoint"
    MODEL = "model"


class EdgeKind(StrEnum):
    CALLS = "calls"
    IMPORTS = "imports"


class IntentStatus(StrEnum):
    ACTIVE = "active"
    DONE = "done"
    ABANDONED = "abandoned"


class ChangeKind(StrEnum):
    NONE = "none"
    ADDED = "added"
    COMPATIBLE = "compatible"
    BREAKING = "breaking"


@dataclass(frozen=True, slots=True)
class Symbol:
    symbol_id: str
    layer: str
    kind: SymbolKind
    path: str
    signature: str
    body_hash: str
    summary: str | None = None
    updated_at: float = 0.0


@dataclass(frozen=True, slots=True)
class Edge:
    src: str
    dst: str
    kind: EdgeKind
    layer: str


@dataclass(frozen=True, slots=True)
class Intent:
    intent_id: str
    dev_id: str
    goal: str
    produces: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    modifies: tuple[str, ...] = ()
    scope: tuple[str, ...] = ()
    status: IntentStatus = IntentStatus.ACTIVE
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass(frozen=True, slots=True)
class Lease:
    symbol_id: str
    dev_id: str
    heartbeat: float
    ttl_s: int = DEFAULT_LEASE_TTL_S
    intent_id: str | None = None
    sig_before: str | None = None
    sig_after: str | None = None
    change_kind: ChangeKind = ChangeKind.NONE

    def is_active(self, now: float) -> bool:
        return now - self.heartbeat < self.ttl_s


@dataclass
class Store:
    """Thread-safe access to the GrokMesh SQLite database."""

    path: str | Path = ":memory:"
    _conn: sqlite3.Connection = field(init=False, repr=False)
    _lock: threading.RLock = field(init=False, repr=False, default_factory=threading.RLock)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if str(self.path) != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run several writes atomically. Nested calls join the outer transaction."""
        with self._lock:
            if self._conn.in_transaction:
                yield self._conn
                return
            self._conn.execute("BEGIN")
            try:
                yield self._conn
            except BaseException:
                self._conn.rollback()
                raise
            self._conn.commit()

    # ---- symbols ---------------------------------------------------------

    def upsert_symbol(self, symbol: Symbol, now: float | None = None) -> None:
        ts = time.time() if now is None else now
        with self.transaction() as c:
            c.execute(
                """
                INSERT INTO symbol (symbol_id, layer, kind, path, signature, body_hash,
                                    summary, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol_id, layer) DO UPDATE SET
                    kind = excluded.kind, path = excluded.path,
                    signature = excluded.signature, body_hash = excluded.body_hash,
                    summary = excluded.summary, updated_at = excluded.updated_at
                """,
                (
                    symbol.symbol_id,
                    symbol.layer,
                    symbol.kind.value,
                    symbol.path,
                    symbol.signature,
                    symbol.body_hash,
                    symbol.summary,
                    ts,
                ),
            )

    def get_symbol(self, symbol_id: str, layer: str) -> Symbol | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM symbol WHERE symbol_id = ? AND layer = ?", (symbol_id, layer)
            ).fetchone()
        return None if row is None else _symbol(row)

    def symbols_in_layer(self, layer: str, path: str | None = None) -> list[Symbol]:
        sql = "SELECT * FROM symbol WHERE layer = ?"
        args: tuple[str, ...] = (layer,)
        if path is not None:
            sql += " AND path = ?"
            args += (path,)
        with self._lock:
            rows = self._conn.execute(sql + " ORDER BY symbol_id", args).fetchall()
        return [_symbol(r) for r in rows]

    def symbol_layers(self, symbol_id: str) -> list[Symbol]:
        """Return every version of one symbol: base and all overlays."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM symbol WHERE symbol_id = ? ORDER BY layer", (symbol_id,)
            ).fetchall()
        return [_symbol(r) for r in rows]

    def replace_file(
        self,
        layer: str,
        path: str,
        symbols: Iterable[Symbol],
        edges: Iterable[Edge],
        now: float | None = None,
    ) -> None:
        """Replace all symbols and outgoing edges of one file in one layer atomically."""
        symbols = list(symbols)
        edges = list(edges)
        for s in symbols:
            if s.layer != layer or s.path != path:
                raise ValueError(f"symbol {s.symbol_id} is not in {layer}:{path}")
        for e in edges:
            if e.layer != layer:
                raise ValueError(f"edge {e.src}->{e.dst} is not in layer {layer}")
        with self.transaction() as c:
            old_ids = [
                r["symbol_id"]
                for r in c.execute(
                    "SELECT symbol_id FROM symbol WHERE layer = ? AND path = ?", (layer, path)
                )
            ]
            c.executemany(
                "DELETE FROM edge WHERE layer = ? AND src = ?", [(layer, i) for i in old_ids]
            )
            c.execute("DELETE FROM symbol WHERE layer = ? AND path = ?", (layer, path))
            for s in symbols:
                self.upsert_symbol(s, now=now)
            c.executemany(
                "INSERT OR IGNORE INTO edge (src, dst, kind, layer) VALUES (?, ?, ?, ?)",
                [(e.src, e.dst, e.kind.value, e.layer) for e in edges],
            )

    def drop_layer(self, layer: str) -> None:
        """Delete one layer, e.g. an overlay after its work merges into main."""
        with self.transaction() as c:
            c.execute("DELETE FROM symbol WHERE layer = ?", (layer,))
            c.execute("DELETE FROM edge WHERE layer = ?", (layer,))

    # ---- edges -----------------------------------------------------------

    def callers(self, symbol_id: str, kind: EdgeKind = EdgeKind.CALLS) -> list[Edge]:
        """Return edges in every layer that point at ``symbol_id``."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM edge WHERE dst = ? AND kind = ? ORDER BY layer, src",
                (symbol_id, kind.value),
            ).fetchall()
        return [_edge(r) for r in rows]

    def callees(self, symbol_id: str, layer: str) -> list[Edge]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM edge WHERE src = ? AND layer = ? ORDER BY dst",
                (symbol_id, layer),
            ).fetchall()
        return [_edge(r) for r in rows]

    # ---- intents ---------------------------------------------------------

    def save_intent(self, intent: Intent, now: float | None = None) -> Intent:
        ts = time.time() if now is None else now
        created = intent.created_at or ts
        with self.transaction() as c:
            c.execute(
                """
                INSERT INTO intent (intent_id, dev_id, goal, produces, consumes, modifies,
                                    scope, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (intent_id) DO UPDATE SET
                    goal = excluded.goal, produces = excluded.produces,
                    consumes = excluded.consumes, modifies = excluded.modifies,
                    scope = excluded.scope, status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    intent.intent_id,
                    intent.dev_id,
                    intent.goal,
                    json.dumps(list(intent.produces)),
                    json.dumps(list(intent.consumes)),
                    json.dumps(list(intent.modifies)),
                    json.dumps(list(intent.scope)),
                    intent.status.value,
                    created,
                    ts,
                ),
            )
        saved = self.get_intent(intent.intent_id)
        assert saved is not None
        return saved

    def get_intent(self, intent_id: str) -> Intent | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM intent WHERE intent_id = ?", (intent_id,)
            ).fetchone()
        return None if row is None else _intent(row)

    def active_intents(self, exclude_dev: str | None = None) -> list[Intent]:
        sql = "SELECT * FROM intent WHERE status = ?"
        args: tuple[str, ...] = (IntentStatus.ACTIVE.value,)
        if exclude_dev is not None:
            sql += " AND dev_id != ?"
            args += (exclude_dev,)
        with self._lock:
            rows = self._conn.execute(sql + " ORDER BY created_at", args).fetchall()
        return [_intent(r) for r in rows]

    def set_intent_status(
        self, intent_id: str, status: IntentStatus, now: float | None = None
    ) -> None:
        ts = time.time() if now is None else now
        with self.transaction() as c:
            cur = c.execute(
                "UPDATE intent SET status = ?, updated_at = ? WHERE intent_id = ?",
                (status.value, ts, intent_id),
            )
            if cur.rowcount == 0:
                raise KeyError(intent_id)

    # ---- leases ----------------------------------------------------------

    def touch_lease(self, lease: Lease) -> None:
        """Create a lease or renew its heartbeat.

        On renewal ``sig_before`` keeps its first value, so it always holds the
        signature from before the developer started the change.
        """
        with self.transaction() as c:
            c.execute(
                """
                INSERT INTO lease (symbol_id, dev_id, intent_id, heartbeat, ttl_s,
                                   sig_before, sig_after, change_kind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol_id, dev_id) DO UPDATE SET
                    intent_id = COALESCE(excluded.intent_id, lease.intent_id),
                    heartbeat = excluded.heartbeat, ttl_s = excluded.ttl_s,
                    sig_before = COALESCE(lease.sig_before, excluded.sig_before),
                    sig_after = excluded.sig_after, change_kind = excluded.change_kind
                """,
                (
                    lease.symbol_id,
                    lease.dev_id,
                    lease.intent_id,
                    lease.heartbeat,
                    lease.ttl_s,
                    lease.sig_before,
                    lease.sig_after,
                    lease.change_kind.value,
                ),
            )

    def get_lease(self, symbol_id: str, dev_id: str) -> Lease | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM lease WHERE symbol_id = ? AND dev_id = ?", (symbol_id, dev_id)
            ).fetchone()
        return None if row is None else _lease(row)

    def active_leases(
        self,
        symbol_ids: Iterable[str] | None = None,
        exclude_dev: str | None = None,
        now: float | None = None,
    ) -> list[Lease]:
        ts = time.time() if now is None else now
        sql = "SELECT * FROM lease WHERE ? - heartbeat < ttl_s"
        args: list[object] = [ts]
        if symbol_ids is not None:
            ids = list(symbol_ids)
            if not ids:
                return []
            sql += f" AND symbol_id IN ({','.join('?' * len(ids))})"
            args += ids
        if exclude_dev is not None:
            sql += " AND dev_id != ?"
            args.append(exclude_dev)
        with self._lock:
            rows = self._conn.execute(sql + " ORDER BY symbol_id, dev_id", args).fetchall()
        return [_lease(r) for r in rows]

    def release_symbol_lease(self, symbol_id: str, dev_id: str) -> None:
        """Release one developer's claim when a symbol is reverted."""
        with self.transaction() as c:
            c.execute("DELETE FROM lease WHERE symbol_id = ? AND dev_id = ?", (symbol_id, dev_id))

    def release_leases(self, dev_id: str, intent_id: str | None = None) -> int:
        sql = "DELETE FROM lease WHERE dev_id = ?"
        args: tuple[str, ...] = (dev_id,)
        if intent_id is not None:
            sql += " AND intent_id = ?"
            args += (intent_id,)
        with self.transaction() as c:
            return c.execute(sql, args).rowcount

    def expire_leases(self, now: float | None = None) -> int:
        ts = time.time() if now is None else now
        with self.transaction() as c:
            return c.execute("DELETE FROM lease WHERE ? - heartbeat >= ttl_s", (ts,)).rowcount


def _symbol(r: sqlite3.Row) -> Symbol:
    return Symbol(
        symbol_id=r["symbol_id"],
        layer=r["layer"],
        kind=SymbolKind(r["kind"]),
        path=r["path"],
        signature=r["signature"],
        body_hash=r["body_hash"],
        summary=r["summary"],
        updated_at=r["updated_at"],
    )


def _edge(r: sqlite3.Row) -> Edge:
    return Edge(src=r["src"], dst=r["dst"], kind=EdgeKind(r["kind"]), layer=r["layer"])


def _intent(r: sqlite3.Row) -> Intent:
    return Intent(
        intent_id=r["intent_id"],
        dev_id=r["dev_id"],
        goal=r["goal"],
        produces=tuple(json.loads(r["produces"])),
        consumes=tuple(json.loads(r["consumes"])),
        modifies=tuple(json.loads(r["modifies"])),
        scope=tuple(json.loads(r["scope"])),
        status=IntentStatus(r["status"]),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


def _lease(r: sqlite3.Row) -> Lease:
    return Lease(
        symbol_id=r["symbol_id"],
        dev_id=r["dev_id"],
        intent_id=r["intent_id"],
        heartbeat=r["heartbeat"],
        ttl_s=r["ttl_s"],
        sig_before=r["sig_before"],
        sig_after=r["sig_after"],
        change_kind=ChangeKind(r["change_kind"]),
    )
