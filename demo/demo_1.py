"""Terminal 1 · backend agent (tim): changes the login endpoint contract.

Start the broker first, from the repository root:
    uv run python -m grokmesh.server --db mesh.db --base-root .
Then, in two terminals:
    uv run python demo/demo_1.py      # backend, tim
    uv run python demo/demo_2.py      # frontend, anna
Set GROKMESH_URL to use a tunnel, e.g. https://<host>.trycloudflare.com/mcp.
Each developer may work on any git branch: the broker sees uncommitted work, not branches.
"""

from __future__ import annotations

from pathlib import Path

from _agent import GREEN, RESET, Agent, run, say, show, step

API = Path(__file__).with_name("api.py")
NEW_API = API.read_text().replace(
    'def login(user_id: str) -> dict[str, str]:\n    return {"token": issue(user_id)}',
    "def login(user_id: str, password: str) -> dict[str, str]:\n"
    "    if not password:\n"
    '        raise ValueError("password required")\n'
    '    return {"token": issue(user_id), "expires_at": "30m"}',
)


async def script(tim: Agent) -> None:
    assert API.read_text() != NEW_API, "demo/api.py changed; update demo_1.py"

    step("[1] Tim's bot declares its task: add a password and token expiry to login()")
    res = await tim.call(
        "declare_intent", goal="Password + token expiry on login", modifies=["demo.api.login"]
    )
    show(res)
    intent_id = res["intent"]["intent_id"]
    say("tim", f"{GREEN}lease granted on demo.api.login{RESET}")

    step("[2] Tim's bot edits demo/api.py and syncs it (uncommitted, on its own branch)")
    res = await tim.call("sync_file", path="demo/api.py", source=NEW_API, intent_id=intent_id)
    show(res)
    say("tim", f"{GREEN}published: login(user_id, password) -> token + expires_at{RESET}")

    step("[3] Tim's bot checks who depends on its change (run after demo_2 step 2)")
    res = await tim.call("get_collision_digest", dev_id="tim")
    for dev in res["developers"]:
        for c in dev["collisions"]:
            print(f"  {c['message'].splitlines()[0]}")
    if not res["developers"]:
        say("tim", "no callers in other agents' work yet")

    step("[4] Tim finishes the task and releases the lease")
    res = await tim.call("close_intent", intent_id=intent_id)
    say("tim", f"released {res['released_leases']} lease(s)")


if __name__ == "__main__":
    run("tim", script)
