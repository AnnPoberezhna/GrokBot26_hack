"""Collision report shared by every detection stage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class CollisionKind(StrEnum):
    SAME_SYMBOL = "same_symbol"
    BROKEN_CONTRACT = "broken_contract"
    DUPLICATION = "duplication"
    INTENT_CONFLICT = "intent_conflict"


class Severity(StrEnum):
    BLOCK = "block"
    WARN = "warn"


class Resolution(StrEnum):
    REUSE = "reuse"
    CODE_AGAINST_STUB = "code_against_stub"
    NEGOTIATE = "negotiate"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class Collision:
    kind: CollisionKind
    severity: Severity
    symbol_id: str
    other_dev: str
    message: str
    other_intent_id: str | None = None
    other_goal: str | None = None
    sig_before: str | None = None
    sig_after: str | None = None
    age_s: float | None = None
    resolutions: tuple[Resolution, ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready dict for MCP tool responses."""
        data = asdict(self)
        data["kind"] = self.kind.value
        data["severity"] = self.severity.value
        data["resolutions"] = [r.value for r in self.resolutions]
        return data


def symbols_overlap(a: str, b: str) -> bool:
    """True if one symbol contains the other: ``auth.S`` and ``auth.S.run``."""
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")


def format_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)} s ago"
    return f"{int(seconds // 60)} min ago"
