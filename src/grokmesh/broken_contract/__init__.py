"""Conservative Python signature comparison and leased caller impact checks."""

from __future__ import annotations

import ast
import time
from collections.abc import Iterable

from grokmesh.collision import Collision, CollisionKind, Resolution, Severity
from grokmesh.store import BASE_LAYER, ChangeKind, Store, overlay_layer


def classify_change(before: str | None, after: str | None) -> ChangeKind:
    """Compare call shapes without executing annotations or default expressions.

    Annotation and class-header changes are conservatively breaking. Changed
    default values remain compatible; runtime behavior and subtyping are not checked.
    """
    if before is None:
        return ChangeKind.ADDED
    if after is None:
        return ChangeKind.BREAKING
    if before == after:
        return ChangeKind.NONE
    try:
        old = ast.parse(before + ":\n    pass").body[0]
        new = ast.parse(after + ":\n    pass").body[0]
    except SyntaxError:
        return ChangeKind.BREAKING
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    if (
        not isinstance(old, functions)
        or not isinstance(new, functions)
        or type(old) is not type(new)
    ):
        return ChangeKind.BREAKING
    a, b = old.args, new.args
    old_pos, new_pos = a.posonlyargs + a.args, b.posonlyargs + b.args
    if len(new_pos) < len(old_pos):
        return ChangeKind.BREAKING

    def annotation(node: ast.AST | None) -> str:
        return ast.dump(node) if node is not None else ""

    if annotation(old.returns) != annotation(new.returns):
        return ChangeKind.BREAKING
    for index, param in enumerate(old_pos):
        replacement = new_pos[index]
        if param.arg != replacement.arg and not (
            index < len(a.posonlyargs) and index < len(b.posonlyargs)
        ):
            return ChangeKind.BREAKING
        if index >= len(a.posonlyargs) and index < len(b.posonlyargs):
            return ChangeKind.BREAKING
        if annotation(param.annotation) != annotation(replacement.annotation):
            return ChangeKind.BREAKING
    # New required parameters, or previously optional parameters becoming required.
    if len(new_pos) - len(b.defaults) > len(old_pos) - len(a.defaults):
        return ChangeKind.BREAKING
    old_kw = {p.arg: (p, d) for p, d in zip(a.kwonlyargs, a.kw_defaults, strict=True)}
    new_kw = {p.arg: (p, d) for p, d in zip(b.kwonlyargs, b.kw_defaults, strict=True)}
    for name, (param, default) in old_kw.items():
        if name not in new_kw:
            return ChangeKind.BREAKING
        replacement, new_default = new_kw[name]
        if default is not None and new_default is None:
            return ChangeKind.BREAKING
        if annotation(param.annotation) != annotation(replacement.annotation):
            return ChangeKind.BREAKING
    if any(default is None for name, (_, default) in new_kw.items() if name not in old_kw):
        return ChangeKind.BREAKING
    for old_var, new_var in ((a.vararg, b.vararg), (a.kwarg, b.kwarg)):
        if old_var is not None and (
            new_var is None or annotation(old_var.annotation) != annotation(new_var.annotation)
        ):
            return ChangeKind.BREAKING
    # Extra positional parameters consume values that previously belonged to *args.
    if a.vararg is not None and len(new_pos) != len(old_pos):
        return ChangeKind.BREAKING
    return ChangeKind.COMPATIBLE


def check_contracts(
    store: Store,
    dev_id: str,
    symbol_ids: Iterable[str] | None = None,
    *,
    now: float | None = None,
) -> list[Collision]:
    """Block affected callers; warn providers about other developers' leased callers.

    WIP call edges count when the caller holds an active lease or names the caller
    in ``symbol_ids``. A base edge counts only for ``dev_id`` when it names that
    caller in ``symbol_ids`` and has no overlay version of it yet: the developer
    is about to edit main's caller, and main's caller calls the changed symbol.
    """
    ts = time.time() if now is None else now
    targets = set(symbol_ids) if symbol_ids is not None else None
    leases = store.active_leases(now=ts)
    active = {(lease.symbol_id, lease.dev_id) for lease in leases}
    found: dict[tuple[str, str, str], Collision] = {}
    for lease in leases:
        if lease.change_kind is not ChangeKind.BREAKING:
            continue
        for edge in store.callers(lease.symbol_id):
            if edge.layer.startswith("wip:"):
                caller_dev = edge.layer.removeprefix("wip:")
            elif (
                edge.layer == BASE_LAYER
                and targets is not None
                and edge.src in targets
                and store.get_symbol(edge.src, overlay_layer(dev_id)) is None
            ):
                caller_dev = dev_id
            else:
                continue
            if caller_dev == lease.dev_id:
                continue
            selected = caller_dev == dev_id and targets is not None and edge.src in targets
            if (edge.src, caller_dev) not in active and not selected:
                continue
            if dev_id == caller_dev:
                if targets is not None and edge.src not in targets:
                    continue
                severity, other = Severity.BLOCK, lease.dev_id
            elif dev_id == lease.dev_id:
                if targets is not None and lease.symbol_id not in targets:
                    continue
                severity, other = Severity.WARN, caller_dev
            else:
                continue
            found[(lease.symbol_id, caller_dev, edge.src)] = Collision(
                kind=CollisionKind.BROKEN_CONTRACT,
                severity=severity,
                symbol_id=lease.symbol_id,
                other_dev=other,
                caller_symbol_id=edge.src,
                message=(
                    f"{'CONFLICT' if severity is Severity.BLOCK else 'WARNING'}: "
                    f"{edge.src} ({caller_dev}) calls {lease.symbol_id} "
                    f"({lease.dev_id}), whose contract changed.\n"
                    f"Change: {lease.sig_before} -> {lease.sig_after or '(deleted)'}"
                ),
                other_intent_id=lease.intent_id if other == lease.dev_id else None,
                sig_before=lease.sig_before,
                sig_after=lease.sig_after,
                age_s=ts - lease.heartbeat,
                resolutions=(Resolution.CODE_AGAINST_STUB, Resolution.ESCALATE),
            )
    return [found[key] for key in sorted(found)]
