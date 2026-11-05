"""BM25 text-search fallback for possible duplication; warnings are unconfirmed."""

from __future__ import annotations

import re
import time

from grokmesh.collision import Collision, CollisionKind, Resolution, Severity
from grokmesh.store import Intent, Store

_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "with",
        "add",
        "build",
        "create",
        "implement",
        "support",
        "def",
        "async",
        "class",
        "return",
        "self",
        "cls",
        "str",
        "int",
        "bool",
        "none",
    ]
)


def _terms(text: str) -> set[str]:
    # Use literal words, never accept FTS operators supplied by a prompt.
    return {word for word in re.findall(r"[^\W_]+", text.lower()) if len(word) >= 3} - _STOP


def check_duplication(
    store: Store,
    intent: Intent,
    *,
    now: float | None = None,
    limit: int = 5,
) -> list[Collision]:
    """Rank teammates' active work by BM25; require two distinct shared terms.

    Matches are lexical evidence, not semantic judgments. Query size, candidate
    count and output are bounded. Own work, base symbols and expired leases are
    excluded. Intents remain eligible until closed.
    """
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    terms = sorted(_terms(" ".join((intent.goal, *intent.produces, *intent.modifies))))[:32]
    if len(terms) < 2:
        return []
    query = " OR ".join(f'"{term}"' for term in terms)
    ts = time.time() if now is None else now
    targets = set((*intent.produces, *intent.modifies))
    results: list[Collision] = []
    seen: set[tuple[str, str]] = set()
    with store.transaction() as connection:
        rows = connection.execute(
            """
            SELECT w.*, bm25(work_search) AS score
            FROM work_search w
            WHERE work_search MATCH ? AND w.dev_id != ? AND (
                (w.kind = 'symbol' AND w.layer LIKE 'wip:%' AND EXISTS (
                    SELECT 1 FROM lease l WHERE l.symbol_id = w.symbol_id
                    AND l.dev_id = w.dev_id AND ? - l.heartbeat < l.ttl_s
                )) OR (w.kind = 'intent' AND EXISTS (
                    SELECT 1 FROM intent i WHERE i.intent_id = w.intent_id AND i.status = 'active'
                ))
            )
            ORDER BY score, w.kind, w.dev_id, w.symbol_id, w.intent_id LIMIT 100
            """,
            (query, intent.dev_id, ts),
        ).fetchall()
        for row in rows:
            shared = set(terms) & _terms(row["content"])
            if len(shared) < 2:
                continue
            other = store.get_intent(row["intent_id"]) if row["kind"] == "intent" else None
            symbol = store.get_symbol(row["symbol_id"], row["layer"]) if other is None else None
            other_targets = (*other.produces, *other.modifies) if other else (row["symbol_id"],)
            if targets.intersection(other_targets):
                continue  # Exact conflicts already have deterministic reports.
            symbol_id = next(iter(other_targets), f"intent:{row['intent_id']}")
            key = (row["dev_id"], symbol_id)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                Collision(
                    kind=CollisionKind.DUPLICATION,
                    severity=Severity.WARN,
                    symbol_id=symbol_id,
                    other_dev=row["dev_id"],
                    other_intent_id=other.intent_id if other else None,
                    other_goal=other.goal if other else None,
                    sig_after=symbol.signature if symbol else None,
                    message=(
                        f"Possible duplicate: {row['dev_id']} is working on {symbol_id}.\n"
                        f"BM25 text match (unconfirmed): {', '.join(sorted(shared))}.\n"
                        "Review the existing work before implementing another version."
                    ),
                    resolutions=(
                        Resolution.REUSE,
                        Resolution.CODE_AGAINST_STUB,
                        Resolution.ESCALATE,
                    ),
                )
            )
            if len(results) >= limit:
                break
    return results
