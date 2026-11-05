"""Exercise the real MCP HTTP transport and tool serialization in process."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from grokmesh.intents import close_intent
from grokmesh.parser import parse_file
from grokmesh.server import create_server
from grokmesh.store import Lease, Store


@asynccontextmanager
async def client(store: Store) -> AsyncIterator[ClientSession]:
    server = create_server(store)
    app = server.streamable_http_app()

    async with (
        server.session_manager.run(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as http_client,
        streamable_http_client("http://localhost:8000/mcp", http_client=http_client) as streams,
    ):
        read, write, _ = streams
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def test_two_developers_over_http() -> None:
    async def scenario() -> None:
        with Store() as store:
            async with client(store) as session:
                listed = await session.list_tools()
                assert {t.name for t in listed.tools} == {
                    "declare_intent",
                    "sync_file",
                    "check_collision",
                    "get_contracts",
                    "close_intent",
                    "get_activity",
                    "get_collision_digest",
                }
                first = await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "anna",
                        "goal": "Build auth",
                        "produces": ["auth.issue"],
                    },
                )
                assert not first.isError
                assert first.structuredContent is not None
                assert first.structuredContent["blocked"] is False
                intent_id = first.structuredContent["intent"]["intent_id"]
                second = await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "marcel",
                        "goal": "Also auth",
                        "modifies": ["auth.issue"],
                    },
                )
                assert second.structuredContent is not None
                assert second.structuredContent["blocked"] is True
                assert second.structuredContent["collisions"][0]["other_dev"] == "anna"
                assert len(store.active_intents()) == 1
                upload = {
                    "dev_id": "anna",
                    "path": "auth.py",
                    "module": "auth",
                    "source": "def issue(token: str) -> str:\n    return token\n",
                    "intent_id": intent_id,
                }
                synced = await session.call_tool("sync_file", upload)
                assert not synced.isError
                contracts = await session.call_tool("get_contracts", {"symbol_ids": ["auth.issue"]})
                assert contracts.structuredContent is not None
                contract = contracts.structuredContent["contracts"][0]
                assert contract["signature"] == "def issue(token: str) -> str"
                assert contract["owner"] == "anna" and contract["active"]
                conflict = await session.call_tool(
                    "sync_file",
                    {
                        **upload,
                        "dev_id": "marcel",
                        "intent_id": None,
                    },
                )
                assert conflict.structuredContent is not None
                assert conflict.structuredContent["blocked"] is True
                assert store.symbols_in_layer("wip:marcel") == []
                invalid = await session.call_tool("sync_file", {**upload, "source": "def issue(:"})
                assert invalid.isError
                assert store.get_symbol("auth.issue", "wip:anna") is not None
                own = await session.call_tool(
                    "check_collision",
                    {
                        "dev_id": "anna",
                        "symbol_ids": ["auth.issue"],
                    },
                )
                assert own.structuredContent is not None and not own.structuredContent["blocked"]
                close_intent(store, "anna", intent_id)
                store.touch_lease(Lease("auth.issue", "anna", heartbeat=0, ttl_s=1))
                expired = await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "marcel",
                        "goal": "Build auth",
                        "produces": ["auth.issue"],
                    },
                )
                assert expired.structuredContent is not None
                assert expired.structuredContent["blocked"] is False

    asyncio.run(scenario())


AUTH = (
    "def issue(token: str) -> str:\n    return token\n\n\n"
    "def verify(token: str) -> bool:\n    return True\n"
)


def test_claim_is_not_a_deletion_and_base_keeps_unrelated_edits_free() -> None:
    async def scenario() -> None:
        with Store() as store:
            base = parse_file(AUTH, "auth.py", "auth", "base")
            store.replace_file("base", "auth.py", base.symbols, base.edges)
            async with client(store) as session:
                claim = await session.call_tool(
                    "declare_intent",
                    {"dev_id": "anna", "goal": "JWT", "modifies": ["auth.issue"]},
                )
                assert claim.structuredContent is not None
                assert claim.structuredContent["blocked"] is False
                lease = store.get_lease("auth.issue", "anna")
                assert lease is not None
                assert lease.sig_after == lease.sig_before == "def issue(token: str) -> str"

                blocked = await session.call_tool(
                    "check_collision", {"dev_id": "tim", "symbol_ids": ["auth.issue"]}
                )
                assert blocked.structuredContent is not None
                message = blocked.structuredContent["collisions"][0]["message"]
                assert "(deleted)" not in message

                # Tim edits only verify(); module comes from the path.
                synced = await session.call_tool(
                    "sync_file",
                    {
                        "dev_id": "tim",
                        "path": "auth.py",
                        "source": AUTH.replace("return True", "return False"),
                    },
                )
                assert not synced.isError
                assert synced.structuredContent is not None
                assert synced.structuredContent["blocked"] is False
                assert {x.symbol_id for x in store.active_leases() if x.dev_id == "tim"} == {
                    "auth.verify"
                }

    asyncio.run(scenario())


def test_broken_contract_over_http() -> None:
    from grokmesh.parser import parse_file

    async def scenario() -> None:
        with Store() as store:
            base = parse_file("def issue(token):\n    return token\n", "auth.py", "auth", "base")
            store.replace_file("base", "auth.py", base.symbols, base.edges)
            async with client(store) as session:
                caller = await session.call_tool(
                    "sync_file",
                    {
                        "dev_id": "marcel",
                        "path": "api.py",
                        "module": "api",
                        "source": "from auth import issue\ndef login():\n    return issue('a')\n",
                    },
                )
                assert not caller.isError
                provider = await session.call_tool(
                    "sync_file",
                    {
                        "dev_id": "anna",
                        "path": "auth.py",
                        "module": "auth",
                        "source": "def issue(token, salt):\n    return token\n",
                    },
                )
                assert provider.structuredContent is not None
                assert provider.structuredContent["blocked"] is False
                impact = provider.structuredContent["collisions"][0]
                assert impact["caller_symbol_id"] == "api.login"
                assert impact["severity"] == "warn"
                checked = await session.call_tool(
                    "check_collision",
                    {
                        "dev_id": "marcel",
                        "symbol_ids": ["api.login"],
                    },
                )
                assert checked.structuredContent is not None
                assert checked.structuredContent["blocked"] is True
                assert checked.structuredContent["collisions"][0]["kind"] == "broken_contract"
                declared = await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "marcel",
                        "goal": "Edit login",
                        "modifies": ["api.login"],
                    },
                )
                assert declared.structuredContent is not None
                assert declared.structuredContent["blocked"] is True
                # The provider can redeclare work without losing its breaking classification.
                await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "anna",
                        "goal": "Finish auth",
                        "modifies": ["auth.issue"],
                    },
                )
                again = await session.call_tool(
                    "check_collision",
                    {
                        "dev_id": "marcel",
                        "symbol_ids": ["api.login"],
                    },
                )
                assert again.structuredContent is not None and again.structuredContent["blocked"]

    asyncio.run(scenario())


def test_duplication_warns_without_blocking_over_http() -> None:
    async def scenario() -> None:
        with Store() as store:
            async with client(store) as session:
                await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "anna",
                        "goal": "JWT token signing",
                        "produces": ["auth.issue"],
                    },
                )
                result = await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "marcel",
                        "goal": "Build JWT token signing",
                        "produces": ["security.mint"],
                    },
                )
                assert not result.isError
                assert result.structuredContent is not None
                assert result.structuredContent["blocked"] is False
                warnings = result.structuredContent["collisions"]
                assert len(warnings) == 1 and warnings[0]["kind"] == "duplication"
                assert warnings[0]["severity"] == "warn"
                assert warnings[0]["other_dev"] == "anna"
                assert len(store.active_intents()) == 2

    asyncio.run(scenario())


def test_close_intent_releases_claims_and_updates_team_snapshot_over_http() -> None:
    async def scenario() -> None:
        with Store() as store:
            async with client(store) as session:
                declared = await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "anna",
                        "goal": "Build auth",
                        "produces": ["auth.issue"],
                    },
                )
                assert declared.structuredContent is not None
                iid = declared.structuredContent["intent"]["intent_id"]
                activity = await session.call_tool("get_activity", {})
                assert activity.structuredContent is not None
                assert activity.structuredContent["developers"][0]["dev_id"] == "anna"
                wrong_owner = await session.call_tool(
                    "close_intent",
                    {
                        "dev_id": "tim",
                        "intent_id": iid,
                    },
                )
                assert wrong_owner.isError
                assert store.get_lease("auth.issue", "anna") is not None
                invalid_status = await session.call_tool(
                    "close_intent",
                    {
                        "dev_id": "anna",
                        "intent_id": iid,
                        "status": "active",
                    },
                )
                assert invalid_status.isError
                closed = await session.call_tool(
                    "close_intent",
                    {
                        "dev_id": "anna",
                        "intent_id": iid,
                        "status": "abandoned",
                    },
                )
                assert not closed.isError
                assert closed.structuredContent is not None
                assert closed.structuredContent["released_leases"] == 1
                assert closed.structuredContent["status"] == "abandoned"
                repeated = await session.call_tool(
                    "close_intent",
                    {
                        "dev_id": "anna",
                        "intent_id": iid,
                        "status": "abandoned",
                    },
                )
                assert repeated.structuredContent is not None
                assert repeated.structuredContent["released_leases"] == 0
                missing = await session.call_tool(
                    "close_intent",
                    {
                        "dev_id": "anna",
                        "intent_id": "missing",
                    },
                )
                assert missing.isError
                activity = await session.call_tool("get_activity", {})
                assert activity.structuredContent is not None
                assert activity.structuredContent["developers"] == []
                digest = await session.call_tool("get_collision_digest", {})
                assert digest.structuredContent is not None
                assert digest.structuredContent["report_count"] == 0
                takeover = await session.call_tool(
                    "declare_intent",
                    {
                        "dev_id": "tim",
                        "goal": "Build auth",
                        "modifies": ["auth.issue"],
                    },
                )
                assert takeover.structuredContent is not None
                assert takeover.structuredContent["blocked"] is False

    asyncio.run(scenario())
