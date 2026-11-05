"""Read-only dashboard and an isolated, engine-backed presentation demo."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from grokmesh.intents import declare_intent
from grokmesh.leases import sync_file
from grokmesh.mesh_bot import get_activity, get_collision_digest
from grokmesh.parser import parse_file
from grokmesh.store import Store

_STATIC = Path(__file__).parent / "static"


def snapshot(store: Store, *, demo: bool = False) -> dict[str, Any]:
    """Read a consistent snapshot, with bounded graph size and unique team conflicts."""
    ts = time.time()
    with store.transaction() as connection:
        activity = get_activity(store, now=ts)
        digest = get_collision_digest(store, now=ts)
        leases = store.active_leases(now=ts)
        active = {(lease.symbol_id, f"wip:{lease.dev_id}") for lease in leases}
        nodes: dict[str, dict[str, Any]] = {}
        for row in connection.execute("SELECT * FROM symbol ORDER BY layer, symbol_id"):
            if row["layer"] != "base" and (row["symbol_id"], row["layer"]) not in active:
                continue
            node = nodes.setdefault(
                row["symbol_id"],
                {
                    "id": row["symbol_id"],
                    "path": row["path"],
                    "kind": row["kind"],
                    "signature": row["signature"],
                    "owners": [],
                    "versions": [],
                },
            )
            node["versions"].append({"layer": row["layer"], "signature": row["signature"]})
            if row["layer"].startswith("wip:"):
                node["signature"] = row["signature"]
        for lease in leases:
            node = nodes.setdefault(
                lease.symbol_id,
                {
                    "id": lease.symbol_id,
                    "path": None,
                    "kind": "function",
                    "signature": lease.sig_after
                    or lease.sig_before
                    or "Contract not yet published",
                    "owners": [],
                    "versions": [],
                },
            )
            node["owners"].append(lease.dev_id)
        collisions: dict[tuple[str, str, tuple[str, ...], str | None], dict[str, Any]] = {}
        for group in digest["developers"]:
            for report in group["collisions"]:
                participants = tuple(sorted((group["dev_id"], report["other_dev"])))
                key = (
                    report["kind"],
                    report["symbol_id"],
                    participants,
                    report["caller_symbol_id"],
                )
                if key not in collisions or report["severity"] == "block":
                    collisions[key] = {**report, "participants": participants}
        reports = sorted(
            collisions.values(),
            key=lambda r: (
                r["severity"] != "block",
                r["kind"],
                r["symbol_id"],
                r["participants"],
            ),
        )
        affected = {r["symbol_id"] for r in reports}
        for node in nodes.values():
            node["collision"] = node["id"] in affected
        edges = [
            dict(row)
            for row in connection.execute(
                "SELECT DISTINCT src, dst, layer FROM edge WHERE kind = 'calls' ORDER BY src, dst"
            )
            if row["src"] in nodes
            and row["dst"] in nodes
            and (row["layer"] == "base" or (row["src"], row["layer"]) in active)
        ]
        # Prefer active and affected symbols when a real repository has a large base graph.
        chosen = sorted(
            nodes.values(),
            key=lambda n: (
                not n["collision"],
                not bool(n["owners"]),
                n["id"],
            ),
        )[:18]
        chosen_ids = {node["id"] for node in chosen}
        visible_edges = sorted(
            {
                (e["src"], e["dst"])
                for e in edges
                if e["src"] in chosen_ids and e["dst"] in chosen_ids
            }
        )
        return {
            "mode": "demo" if demo else "live",
            "generated_at": ts,
            "developers": activity["developers"],
            "collisions": reports,
            "nodes": chosen,
            "edges": [{"src": src, "dst": dst} for src, dst in visible_edges],
            "metrics": {
                "developers": len(activity["developers"]),
                "symbols": len(nodes),
                "leases": len(leases),
                "blocking": sum(r["severity"] == "block" for r in reports),
                "warnings": sum(r["severity"] == "warn" for r in reports),
            },
        }


def demo_snapshot() -> dict[str, Any]:
    """Generate sample collisions in a separate in-memory database, never the team store."""
    now = time.time()
    files = {
        "auth": "def issue(user_id: str) -> str:\n    return sign(user_id)\n"
        "def sign(token: str) -> str:\n    return token\n"
        "def verify(token: str) -> bool:\n    return True\n",
        "api": "from demo.auth import issue, verify\n"
        "def login(user_id: str):\n    return issue(user_id)\n"
        "def profile(token: str):\n    return verify(token)\n",
        "tokens": "from demo.auth import sign\ndef refresh(token: str):\n    return sign(token)\n"
        "def revoke(token: str):\n    pass\n",
        "audit": "def record(event: str):\n    pass\ndef flush():\n    pass\n",
    }
    with Store() as store:
        for module, source in files.items():
            path = f"demo/{module}.py"
            parsed = parse_file(source, path, f"demo.{module}", "base")
            store.replace_file("base", path, parsed.symbols, parsed.edges, now=now - 600)
        anna = declare_intent(
            store,
            "anna",
            "JWT token signing and issuance",
            modifies=["demo.auth.issue", "demo.auth.sign"],
            scope=["demo/auth.py"],
            now=now - 240,
        )
        marcel = declare_intent(
            store,
            "marcel",
            "Connect login to the authentication contract",
            modifies=["demo.api.login"],
            scope=["demo/api.py"],
            now=now - 180,
        )
        tim = declare_intent(
            store,
            "tim",
            "Build JWT token signing utility",
            produces=["demo.tokens.mint"],
            modifies=["demo.auth.sign"],
            scope=["demo/tokens.py"],
            now=now - 120,
        )
        sync_file(
            store,
            "marcel",
            "demo/api.py",
            "demo.api",
            files["api"].replace("issue(user_id)", "issue(user_id.strip())"),
            intent_id=marcel.intent_id,
            now=now - 45,
        )
        sync_file(
            store,
            "anna",
            "demo/auth.py",
            "demo.auth",
            files["auth"]
            .replace("issue(user_id: str)", "issue(user_id: str, scope: str)")
            .replace("return token", "return token.strip()"),
            intent_id=anna.intent_id,
            now=now - 24,
        )
        sync_file(
            store,
            "tim",
            "demo/tokens.py",
            "demo.tokens",
            files["tokens"] + "def mint(jwt_token: str):\n    return sign(jwt_token)\n",
            intent_id=tim.intent_id,
            now=now - 12,
        )
        return snapshot(store, demo=True)


def register_dashboard(server: FastMCP[Any], store: Store) -> None:
    async def index(request: Request) -> Response:
        return Response(
            (_STATIC / "index.html").read_bytes(),
            media_type="text/html",
            headers={"Cache-Control": "no-cache"},
        )

    async def asset(request: Request) -> Response:
        filename = request.path_params["filename"]
        if filename not in {"styles.css", "app.js"}:
            return Response(status_code=404)
        return Response(
            (_STATIC / filename).read_bytes(),
            media_type="text/css" if filename.endswith(".css") else "text/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    async def data(request: Request) -> Response:
        result = demo_snapshot() if request.query_params.get("demo") == "1" else snapshot(store)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    server.custom_route("/", methods=["GET"], include_in_schema=False)(index)
    server.custom_route("/assets/{filename}", methods=["GET"], include_in_schema=False)(asset)
    server.custom_route("/api/dashboard", methods=["GET"], include_in_schema=False)(data)
