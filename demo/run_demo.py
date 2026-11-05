"""Scripted GrokMesh demo for the 90-second pitch.

It calls the same MCP tool functions that the Grok Bots call over HTTP, on an
in-memory store with the ``demo/`` app as the base layer. No network, no LLM.

Run:
    uv run python demo/run_demo.py          # press Enter to advance each step
    uv run python demo/run_demo.py --auto   # timed steps, for screen recording
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from grokmesh.leases import index_base
from grokmesh.server import create_server
from grokmesh.store import Store

ROOT = Path(__file__).resolve().parent.parent
CYAN, GREEN, YELLOW, RED = "\033[96m", "\033[92m", "\033[93m", "\033[91m"
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


class Stage:
    def __init__(self, auto: bool, delay: float) -> None:
        self.auto = auto
        self.delay = delay

    def step(self, number: int, title: str) -> None:
        if self.auto:
            time.sleep(self.delay)
        else:
            input(f"{DIM}[Enter]{RESET}")
        print(f"\n{BOLD}{CYAN}[{number}] {title}{RESET}")

    def call(self, who: str, text: str) -> None:
        print(f"  {who:<8} {BOLD}{text}{RESET}")
        time.sleep(0.4 if self.auto else 0)


def show_collisions(result: dict[str, Any]) -> None:
    for c in result["collisions"]:
        color = RED if c["severity"] == "block" else YELLOW
        for line in c["message"].splitlines():
            print(f"  {color}{line}{RESET}")
        print(f"  {DIM}resolutions: {', '.join(c['resolutions'])}{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auto", action="store_true", help="advance automatically")
    parser.add_argument("--delay", type=float, default=2.5, help="seconds per step with --auto")
    args = parser.parse_args()
    stage = Stage(args.auto or not sys.stdin.isatty(), args.delay)

    print(f"\n{BOLD}{GREEN}GrokMesh: one live code graph for every coding agent on the team{RESET}")
    with Store() as store:
        index_base(store, ROOT)
        server = create_server(store)

        def tool(name: str) -> Callable[..., dict[str, Any]]:
            found = server._tool_manager.get_tool(name)
            assert found is not None, name
            return found.fn  # type: ignore[no-any-return]

        declare, sync, contracts, activity = (
            tool("declare_intent"),
            tool("sync_file"),
            tool("get_contracts"),
            tool("get_activity"),
        )
        print(f"{DIM}base layer: demo/auth.py, demo/api.py (api.login calls auth.issue){RESET}")

        stage.step(1, "Anna's bot declares its intent before it writes code")
        stage.call("anna", "declare_intent(modifies=['demo.auth.issue'], goal='Add token expiry')")
        anna = declare("anna", "Add token expiry", modifies=["demo.auth.issue"])
        print(f"  {GREEN}granted: lease on demo.auth.issue for 30 min{RESET}")

        stage.step(2, "Marcel's bot wants the same function")
        stage.call("marcel", "declare_intent(modifies=['demo.auth.issue'], goal='Rewrite signing')")
        blocked = declare("marcel", "Rewrite token signing", modifies=["demo.auth.issue"])
        print(f"  {BOLD}{RED}BLOCKED{RESET} before a single line of duplicate code")
        show_collisions(blocked)

        stage.step(3, "Anna changes the contract of issue()")
        source = (
            (ROOT / "demo" / "auth.py")
            .read_text()
            .replace(
                "def issue(user_id: str) -> str:", "def issue(user_id: str, ttl_s: int) -> str:"
            )
        )
        stage.call("anna", "sync_file('demo/auth.py')  ->  issue(user_id, ttl_s)")
        sync("anna", "demo/auth.py", source, intent_id=anna["intent"]["intent_id"])
        print(f"  {GREEN}overlay published; signature change classified as BREAKING{RESET}")

        stage.step(4, "Marcel's bot plans to edit login(), which calls issue()")
        stage.call("marcel", "declare_intent(modifies=['demo.api.login'], goal='Add audit log')")
        impact = declare("marcel", "Add audit log to login", modifies=["demo.api.login"])
        print(f"  {BOLD}{RED}BLOCKED{RESET}: broken contract found before merge, not after")
        show_collisions(impact)

        stage.step(5, "Marcel's bot pulls the new contract and codes against it")
        stage.call("marcel", "get_contracts(['demo.auth.issue'])")
        for c in contracts(["demo.auth.issue"])["contracts"]:
            owner = c["owner"] or "main"
            print(f"  {GREEN}{c['signature']:<45}{RESET} {DIM}{owner}{RESET}")

        stage.step(6, "Mesh Bot: who works on what")
        stage.call("mesh", "get_activity()")
        for dev in activity()["developers"]:
            for intent in dev["intents"]:
                print(f"  {dev['dev_id']:<8} {intent['goal']}")
            for lease in dev["leases"]:
                print(f"  {'':<8} {DIM}{lease['symbol_id']} ({lease['change_kind']}){RESET}")

    print(
        f"\n{BOLD}{GREEN}Collisions caught at intent time: same symbol, broken contract.{RESET}\n"
    )


if __name__ == "__main__":
    main()
