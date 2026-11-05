"""The dashboard reads broker state; presentation data must never mutate it."""

import asyncio

import httpx

from grokmesh.dashboard import snapshot
from grokmesh.leases import sync_file
from grokmesh.server import create_server
from grokmesh.store import Store


def test_dashboard_routes_and_demo_isolation() -> None:
    async def scenario() -> None:
        with Store() as store:
            server = create_server(store)
            app = server.streamable_http_app()
            async with (
                server.session_manager.run(),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://localhost:8000",
                ) as client,
            ):
                page = await client.get("/")
                assert page.status_code == 200
                assert "GrokMesh" in page.text
                assert (await client.get("/assets/app.js")).status_code == 200
                assert (await client.get("/assets/styles.css")).status_code == 200
                assert (await client.get("/assets/store.py")).status_code == 404
                assert (await client.get("/api/dashboard")).json()["metrics"]["symbols"] == 0
                demo = (await client.get("/api/dashboard?demo=1")).json()
                assert demo["mode"] == "demo"
                assert demo["metrics"]["developers"] == 3
                assert {r["kind"] for r in demo["collisions"]} == {
                    "same_symbol",
                    "broken_contract",
                    "duplication",
                }
                assert demo["edges"] and demo["nodes"]
                # Demo mode has not created real intents, symbols, or leases.
                live = (await client.get("/api/dashboard")).json()
                assert live["mode"] == "live"
                assert live["nodes"] == []
                assert live["developers"] == []
                assert live["collisions"] == []
                sync_file(store, "anna", "auth.py", "auth", "def issue():\n    pass\n")
                updated = (await client.get("/api/dashboard")).json()
                assert updated["metrics"]["leases"] == 1
                assert updated["nodes"][0]["owners"] == ["anna"]

    asyncio.run(scenario())


def test_expired_overlays_are_not_active_graph_nodes() -> None:
    with Store() as store:
        sync_file(store, "anna", "auth.py", "auth", "def issue():\n    pass\n", now=0, ttl_s=1)
        data = snapshot(store)
        assert data["metrics"]["leases"] == 0
        assert data["nodes"] == []
