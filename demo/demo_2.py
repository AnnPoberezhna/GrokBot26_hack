"""Terminal 2 · frontend agent (anna): wires a client to the login endpoint.

Run demo_1.py steps 1–2 first. See demo_1.py for the broker command.
"""

from __future__ import annotations

from _agent import DIM, GREEN, RESET, YELLOW, Agent, run, say, show, step

NAIVE = '''"""Client used by the login form."""

from demo.api import login


def sign_in(user_id: str) -> str:
    return login(user_id)["token"]
'''

ADAPTED = '''"""Client used by the login form."""

from demo.api import login


def sign_in(user_id: str, password: str) -> tuple[str, str]:
    res = login(user_id, password)
    return res["token"], res["expires_at"]
'''


async def script(anna: Agent) -> None:
    step("[1] Anna's bot declares a separate task: a login client for the form")
    res = await anna.call(
        "declare_intent",
        goal="Login form client",
        produces=["demo.client.sign_in"],
        consumes=["demo.api.login"],
    )
    show(res)
    intent_id = res["intent"]["intent_id"]
    say("anna", f"{GREEN}not blocked: a different task{RESET} (warnings above are hints only)")

    step("[2] Anna's bot writes the client against main's login(user_id) and syncs it")
    res = await anna.call("sync_file", path="demo/client.py", source=NAIVE, intent_id=intent_id)
    show(res)
    if res["collisions"]:
        say(
            "anna",
            f"{YELLOW}GrokMesh: the endpoint I call is changing in Tim's work right now{RESET}",
        )

    step("[3] Anna's bot pulls the current contract, including Tim's uncommitted work")
    res = await anna.call("get_contracts", symbol_ids=["demo.api.login"])
    for c in res["contracts"]:
        owner = c["owner"] or "main"
        print(f"  {owner:<6} {c['signature']}")

    step("[4] Anna's bot adapts on the fly and syncs again")
    res = await anna.call("sync_file", path="demo/client.py", source=ADAPTED, intent_id=intent_id)
    for c in res["collisions"]:
        edge = f"{c['caller_symbol_id']} -> {c['symbol_id']}"
        print(f"  {DIM}still tracked while Tim's change is open: {edge}{RESET}")
    say(
        "anna",
        f"{GREEN}client now calls login(user_id, password), before either one commits{RESET}",
    )

    step("[5] Anna's bot tries to edit Tim's endpoint directly")
    res = await anna.call(
        "declare_intent", goal="Tweak login response", modifies=["demo.api.login"]
    )
    show(res)

    step("[6] Anna finishes and releases her lease")
    res = await anna.call("close_intent", intent_id=intent_id)
    say("anna", f"released {res['released_leases']} lease(s)")


if __name__ == "__main__":
    run("anna", script)
