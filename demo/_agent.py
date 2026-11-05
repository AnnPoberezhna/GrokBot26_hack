"""Shared helpers for the two-terminal demo: one MCP client per developer."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = os.environ.get("GROKMESH_URL", "http://127.0.0.1:8000/mcp")
CYAN, GREEN, YELLOW, RED = "\033[96m", "\033[92m", "\033[93m", "\033[91m"
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def step(title: str) -> None:
    if os.environ.get("GROKMESH_AUTO") != "1":
        input(f"{DIM}[Enter]{RESET}")
    print(f"\n{BOLD}{CYAN}{title}{RESET}")


def say(who: str, text: str) -> None:
    print(f"  {BOLD}{who}{RESET}  {text}")


def show(result: dict[str, Any]) -> None:
    if result.get("blocked"):
        print(f"  {BOLD}{RED}BLOCKED{RESET}")
    for c in result.get("collisions", []):
        color = RED if c["severity"] == "block" else YELLOW
        for line in c["message"].splitlines():
            print(f"  {color}{line}{RESET}")


class Agent:
    def __init__(self, session: ClientSession, dev_id: str) -> None:
        self.session = session
        self.dev_id = dev_id

    async def call(self, tool: str, **args: Any) -> dict[str, Any]:
        args = {"dev_id": self.dev_id, **args} if tool not in {"get_contracts"} else args
        shown = ", ".join(f"{k}={v!r}" for k, v in args.items() if k not in {"dev_id", "source"})
        say(self.dev_id, f"{DIM}→ {tool}({shown}){RESET}")
        res = await self.session.call_tool(tool, args)
        if res.isError:
            text = " ".join(getattr(c, "text", "") for c in res.content)
            raise RuntimeError(f"{tool} failed: {text}")
        if res.structuredContent is not None:
            return dict(res.structuredContent)
        return dict(json.loads(res.content[0].text))  # type: ignore[union-attr]


def run(dev_id: str, script: Callable[[Agent], Awaitable[None]]) -> None:
    async def main() -> None:
        print(f"{BOLD}{GREEN}GrokMesh agent · {dev_id}{RESET}  {DIM}{URL}{RESET}")
        async with streamable_http_client(URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await script(Agent(session, dev_id))

    asyncio.run(main())
