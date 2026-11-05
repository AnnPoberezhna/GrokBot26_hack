# GrokMesh

**GrokMesh lets the coding agents of a whole team see each other's work in progress.
It finds collisions when an agent declares its intent, not at the pull request.**

Built at the Grok Bot Hackathon Wrocław on 5 November 2026, 18:00–21:10.

▶ **Pitch film: [watch on Google Drive](https://drive.google.com/file/d/1du6Yc3zhX4lK0cMfT5Y62wtsjHhJ0tpo/view?usp=sharing)** (72 s, no sound).
The same file is in the repository: [docs/grokmesh-pitch-kanzen.mp4](docs/grokmesh-pitch-kanzen.mp4).

## Summary

| | |
| --- | --- |
| **Problem** | Each developer runs a coding agent. Each agent works alone. Two agents can finish separate tasks, pass their own tests, and still break each other. |
| **Example** | The frontend bot calls `login(user_id)`. The backend bot changes it to `login(user_id, password)`. Git finds the mismatch at merge. |
| **Idea** | GrokMesh moves the check from the pull request to the moment an agent declares its intent. |
| **How** | Each Grok Bot connects to one GrokMesh broker over MCP. The broker keeps a live code graph of all uncommitted work. |
| **Result** | Before a bot calls a teammate's function, it reads the current contract, including the teammate's uncommitted change. The bot adapts its code before either developer commits. |
| **Stack** | Python 3.12, SQLite, FastMCP over Streamable HTTP. 7 MCP tools, 76 tests. |

## How it works

1. **Declare.** A bot calls `declare_intent` with the symbols it will produce or modify.
2. **Sync.** After each edit, the bot sends the changed file with `sync_file`.
3. **Index.** The broker parses the file. It stores symbols, signatures, body hashes and call edges. It does not store source code.
4. **Layer.** The `main` branch is the base layer. Each developer has an overlay with uncommitted symbols.
5. **Lease.** Each changed symbol gets a lease for its developer. A lease expires after 30 minutes without a sync.
6. **Check.** The broker runs the checks below. A declaration runs all three stages. A sync runs stages 1 and 2.

| Stage | Collision | Rule | Effect |
| --- | --- | --- | --- |
| 1 | Same symbol | Another developer holds an active lease or intent on the symbol. | Block |
| 2 | Broken contract | A symbol has a breaking signature change, and a `calls` edge leads to another developer's work. | Block |
| 3 | Duplication | BM25 text search finds a similar intent or symbol of another developer. | Warn |

Each report names the other developer and the possible resolutions. A contract report also shows the before and after signatures.

## Present the project

The jury limit is 90 seconds. Use one of these three formats.

| Format | Command | Use when |
| --- | --- | --- |
| **Film** | Play it from [Google Drive](https://drive.google.com/file/d/1du6Yc3zhX4lK0cMfT5Y62wtsjHhJ0tpo/view?usp=sharing) or [docs/grokmesh-pitch-kanzen.mp4](docs/grokmesh-pitch-kanzen.mp4) | You want a fixed 72-second pitch. The repository copy plays offline. |
| **Two-terminal live demo** | See [Live demo](#live-demo-two-agents-two-terminals) | You want to show real MCP traffic between two agents. |
| **Dashboard** | Start the broker, open `http://127.0.0.1:8000/` | You want a visual graph of leases and collisions. |

Suggested live pitch:

1. **0:00–0:20.** State the problem with the frontend and backend example.
2. **0:20–1:10.** Run the two-terminal demo, steps 1 to 5.
3. **1:10–1:30.** Close: "Sync at intent, not at the pull request."

## Live demo: two agents, two terminals

Each script is a real MCP client. It talks to the broker over HTTP, like a Grok Bot.
The two developers can work on different git branches. The broker sees uncommitted work, not branches.

```sh
rm -f demo.db*                                               # start from a clean state
uv run python -m grokmesh.server --db demo.db --base-root .  # terminal 0: broker
uv run python demo/demo_1.py                                 # terminal 1: Tim, backend
uv run python demo/demo_2.py                                 # terminal 2: Anna, frontend
```

Press Enter to go to the next step. Run steps 1 and 2 of `demo_1.py` before you start `demo_2.py`.

| Step | Terminal | What happens |
| --- | --- | --- |
| 1 | Tim | Declares an intent on `demo.api.login`. Gets a lease. |
| 2 | Tim | Syncs `login(user_id, password)`. The broker classifies the change as breaking. |
| 1 | Anna | Declares a separate task: a login client. Not blocked. |
| 2 | Anna | Syncs a client that calls `login(user_id)`. Gets a broken-contract report that names Tim. |
| 3 | Anna | Calls `get_contracts`. Sees the `main` signature and Tim's uncommitted signature. |
| 4 | Anna | Adapts the client to `login(user_id, password)` and syncs again. |
| 5 | Anna | Tries to modify `demo.api.login`. Gets **BLOCKED**: Tim holds the lease. |

Notes:

- Use a new database for each run. An overlay from an earlier run blocks Anna's step 1.
- After step 4, the broker still reports the dependency while Tim's change is open. GrokMesh does not check call arguments.
- To use a public tunnel, set `GROKMESH_URL=https://<host>.trycloudflare.com/mcp`.
- `uv run python demo/run_demo.py` runs a scripted version in one terminal, with no network.

## Run the broker

```sh
uv sync
uv run python -m grokmesh.server --db mesh.db --base-root path/to/main/checkout
```

- **MCP endpoint:** `http://127.0.0.1:8000/mcp` (Streamable HTTP).
- **Dashboard:** `http://127.0.0.1:8000/`.
- **`--base-root`:** builds the base layer from a checkout of `main` at startup. Always set it. Without a base layer, every symbol in a synced file counts as changed.
- **`--host`, `--port`:** change the listen address. The defaults are `127.0.0.1` and `8000`.
- **State:** the SQLite file keeps team state across restarts.

### Connect a Grok Bot through a public tunnel

Grok Bot cannot reach `127.0.0.1`. Expose the broker with a tunnel:

```sh
cloudflared tunnel --url http://127.0.0.1:8000
uv run python -m grokmesh.server --db mesh.db --base-root . --public-host <host>.trycloudflare.com
```

Then ask the bot: "Add a custom MCP server named GrokMesh at `https://<host>.trycloudflare.com/mcp` using Streamable HTTP."

The broker has no authentication. Each client sends its own `dev_id`. Use it only with trusted participants.

## MCP tools

| Tool | Inputs | Result |
| --- | --- | --- |
| `declare_intent` | `dev_id`, `goal`; optional `produces`, `consumes`, `modifies`, `scope` | An intent ID and 30-minute leases, or `blocked: true` with the collisions. A blocked call writes nothing. |
| `sync_file` | `dev_id`, `path`, `source`; optional `module`, `intent_id`, `ttl_s` | The published symbols and impact warnings, or `blocked: true`. |
| `check_collision` | `dev_id`, `symbol_ids` | The collisions for these symbols and a `blocked` flag. |
| `get_contracts` | `symbol_ids` | The signatures in the base layer and in every overlay, with owner and lease state. |
| `close_intent` | `dev_id`, `intent_id`; optional `status` (`done`, `abandoned`) | Closes the intent and releases its leases. |
| `get_activity` | optional `dev_id` | Active goals, scopes and leased symbols for each developer. |
| `get_collision_digest` | optional `dev_id` | Current collisions for each developer, blocking reports first. |

Rules for a bot:

1. Call `declare_intent` before you edit code.
2. Stop if a result has `blocked: true`. Show the message to your developer.
3. Call `get_contracts` before you call another developer's function.
4. Call `sync_file` with the full file after each edit.
5. Call `close_intent` when the task is done or abandoned.

Details:

- `module` defaults to the name derived from `path`. Example: `src/pkg/auth.py` becomes `pkg.auth`.
- Only `produces` and `modifies` claim symbols. `consumes` and `scope` are context only.
- An active intent reserves its symbols until its owner closes it, also after its leases expire.
- Closing an intent releases its leases. It does not merge code or delete the overlay.
- Invalid Python returns a tool error and changes nothing.
- One database transaction holds each check and its writes. Two bots cannot claim one symbol at the same time.

## Detection details

**Broken contract.** The broker compares each new signature with the base signature:

- **Compatible:** a new optional parameter, or a changed default value.
- **Breaking:** a removed, renamed or new required parameter, a lost `*args` or `**kwargs`, a sync/async change, any annotation change, any class-header change.

A caller counts when it is in another developer's overlay with an active lease, or when that developer names it in a declaration or a check. Calls inside one developer's work do not count.

**Duplication.** The broker searches other developers' active intents and leased symbols with SQLite FTS5 (BM25).

- A match needs two or more shared words after common words are removed.
- The broker returns at most five warnings. Warnings never block.
- It cannot match synonyms without shared words. Treat each match as a hint.

**Call resolution.** The parser resolves calls to local functions, to `self`/`cls` methods, and through imports, including relative imports. It does not resolve dynamic dispatch or name shadowing.

## Dashboard

Open `http://127.0.0.1:8000/` while the broker runs. No build step is needed.

- **Demo mode** shows three sample developers in a separate in-memory database. It never changes team data.
- **Live workspace** reads the broker's real state every three seconds.
- **Present** hides the sidebar and enlarges the graph. Press `/` to search and Escape to exit.
- Click a symbol or **Explore conflict** to see signatures, contracts and next steps.
- `/api/dashboard` serves the live data. `/api/dashboard?demo=1` serves the sample data. Neither returns source code.

## Repository

| Path | Content |
| --- | --- |
| `src/grokmesh/` | Broker: store, parser, sync and leases, intents, three detection stages, Mesh Bot queries, MCP server, dashboard. |
| `demo/` | Demo app (`auth.py`, `api.py`), the two-terminal demo (`demo_1.py`, `demo_2.py`) and the scripted demo (`run_demo.py`). |
| `tests/` | 76 tests, including MCP over HTTP. |
| `docs/` | [IDEA.md](docs/IDEA.md) (design), [PLAN.md](docs/PLAN.md) (build plan), pitch films. |
| `pitch/` | Remotion source of the films. Render: `cd pitch && pnpm install && pnpm exec remotion render src/index.ts GrokMeshKanzen out/film.mp4`. |
| `sessions/` | AI coding session exports, as the organizers require. |

## Development

```sh
uv run pytest
uv run ruff check .
uv run mypy
```
